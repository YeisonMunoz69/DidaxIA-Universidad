\encoding UTF8
-- ---------------------------------------------------------------------------
-- 14-version-decidible.sql · sin documento legible no hay nada que decidir
-- ---------------------------------------------------------------------------
-- El defecto que esta migración cierra · `C1-A`
-- ---------------------------------------------------------------------------
-- La migración 13 le dio al documento un sitio y la revisión R2 construyó la
-- herramienta para publicarlo. Faltaba lo que las une: **nada exigía que una
-- versión tuviera su documento para poder aceptarse**.
--
-- Reproducido sobre `a1a8db8`, contra PostgreSQL real:
--
--   1. `registrar_version()` crea metadata sin instantánea;
--   2. `didaxia_version_requerida('titular')` la devuelve como la que rige;
--   3. `GET /api/consentimiento/version/<codigo>/texto` responde 404;
--   4. `DecisionConjunta.svelte` habilita «Acepto» —su `publicadas` sólo mira
--      que exista metadata—;
--   5. y el `INSERT` en `consentimiento_evento` **se acepta**: queda registrada
--      la aceptación de un documento que no existe.
--
-- Es el peor desenlace posible de este modelo. Toda la Fase 3 existe para poder
-- demostrar años después qué leyó quien aceptó; una fila que dice «otorgado»
-- apuntando a un texto inexistente no demuestra nada y afirma algo falso.
--
-- Por qué se corrige AQUÍ y no en el adaptador
-- ---------------------------------------------------------------------------
-- Porque `didaxia_version_requerida()` es **la única redacción de la regla**, y
-- la migración 11 lo dice: la usan tres consumidores —el disparador
-- `didaxia_version_del_acto`, `AdaptadorVersionesDeConsentimientoPostgres` y la
-- lectura del estado vigente— «y tres redacciones de la misma regla acabarían
-- eligiendo versiones distintas».
--
-- Corregirla aquí cierra los tres a la vez, y cierra además el que ninguna
-- comprobación de Python alcanza: **el disparador**. Con esto, un `INSERT`
-- directo por SQL crudo contra una versión sin documento se rechaza igual que
-- se rechaza hoy uno contra una versión desplazada — que es la propiedad que
-- `test_sql_crudo_no_puede_saltarse_la_version_requerida` ya exige.
--
-- El backend es la autoridad, y ahora lo es la base: aunque un cliente
-- manipulara la interfaz, la decisión no se puede escribir.
--
-- Las dos condiciones, y por qué las dos
-- ---------------------------------------------------------------------------
-- 1. **La instantánea existe.** Sin cuerpo no hay nada que leer, y aceptar algo
--    que no se puede leer no es consentir.
-- 2. **Su huella corresponde.** Existir no basta: si el cuerpo guardado no es
--    el que `huella_contenido` declara, entonces la huella que la pantalla
--    enseña no identifica el texto — que es exactamente el defecto que la
--    migración 13 vino a cerrar. La comprobación se hace **en la base** porque
--    `sha256(convert_to(cuerpo,'UTF8'))` reproduce byte a byte lo que calcula
--    `dominio/modelo/instantanea_consentimiento.py`: los `CHECK` de la 13
--    garantizan que el cuerpo ya está en forma canónica —sin `\r`, con un único
--    salto final— así que los bytes que PostgreSQL hashea son los mismos que
--    hashea Python. Comprobado con acentos y multilínea.
--
-- ⚠️ NO retrocede a una versión anterior
-- ---------------------------------------------------------------------------
-- Si la más reciente no tiene documento utilizable, el resultado es **NULL**, no
-- «la anterior que sí lo tenga». Retroceder rompería el hito A2 —«publicar
-- términos posteriores desplaza a los previos de forma definitiva»— y dejaría a
-- alguien aceptando un texto ya desplazado porque el vigente está a medio
-- publicar. `NULL` significa que ahora mismo no rige ninguna: el sistema falla
-- cerrado y la pantalla dice «Todavía no puedes decidir», que es la verdad.
--
-- Esa es también la razón de que el `LIMIT 1` siga **dentro** de la subconsulta
-- y las condiciones nuevas se apliquen **después**: elegir primero la que rige y
-- comprobarla después es lo que impide el retroceso. Ponerlas dentro del
-- `WHERE` interno habría hecho que la consulta saltara a la anterior.
--
-- Lo que esta migración NO cambia
-- ---------------------------------------------------------------------------
-- **Ninguna decisión ya registrada.** `consentimiento_evento` es inmutable y no
-- se toca: un acto histórico sigue apuntando a su código y su huella, aunque esa
-- versión nunca llegue a tener instantánea. Lo que cambia es qué se puede
-- aceptar **a partir de ahora**, no qué se aceptó.
--
-- Y **no rellena ninguna instantánea**. Una versión anterior a la migración 13
-- se queda sin documento y por tanto sin poder decidirse: darle un cuerpo ahora
-- sería afirmar que es el que leyeron quienes ya aceptaron, y eso no se puede
-- saber.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION didaxia_version_requerida(el_alcance text) RETURNS text
LANGUAGE sql STABLE AS $funcion$
    SELECT mas_reciente.codigo
      FROM (
          -- Paso 1 · la más reciente que ya comenzó. Intacto respecto de la
          -- migración 11: es lo que impide retroceder a una desplazada.
          SELECT codigo, vigente_hasta, huella_contenido
            FROM consentimiento_version
           WHERE alcance = el_alcance
             AND vigente_desde <= now()
           ORDER BY vigente_desde DESC, codigo DESC
           LIMIT 1
      ) AS mas_reciente
      -- Paso 2 · y sólo entonces, si esa sigue vigente Y es decidible. El
      -- `JOIN` es lo que exige que exista instantánea: sin fila, no hay
      -- resultado, y el resultado es NULL en vez de la anterior.
      JOIN consentimiento_version_texto AS texto
        ON texto.version = mas_reciente.codigo
     WHERE (mas_reciente.vigente_hasta IS NULL OR now() < mas_reciente.vigente_hasta)
       AND encode(sha256(convert_to(texto.cuerpo, 'UTF8')), 'hex')
           = mas_reciente.huella_contenido;
$funcion$;

COMMENT ON FUNCTION didaxia_version_requerida(text) IS
    'La version que rige AHORA en un alcance, o NULL. Tres pasos: la mas '
    'reciente que ya comenzo; despues si sigue vigente; y despues si es '
    'DECIDIBLE, es decir si tiene instantanea y su sha256 coincide con '
    'huella_contenido (C1-A). Nunca retrocede a una anterior: si la vigente no '
    'es decidible el resultado es NULL y el sistema falla cerrado. Unica '
    'redaccion de la regla, usada por el disparador, el adaptador y el estado.';

-- ---------------------------------------------------------------------------
-- didaxia_version_decidible · la misma regla, para una versión concreta
-- ---------------------------------------------------------------------------
-- La usa la lectura del estado para poder decirle al frontend **por qué** no se
-- puede decidir, sin repetir la condición en Python. Es información, no
-- seguridad: quien impide la escritura es el disparador de arriba.
--
-- Se declara aparte y no se deduce de `didaxia_version_requerida()` porque
-- responden preguntas distintas: aquélla dice cuál rige, ésta dice si una
-- cualquiera —incluida una histórica— tiene documento utilizable.
CREATE OR REPLACE FUNCTION didaxia_version_decidible(el_codigo text) RETURNS boolean
LANGUAGE sql STABLE AS $funcion$
    SELECT EXISTS (
        SELECT 1
          FROM consentimiento_version AS version
          JOIN consentimiento_version_texto AS texto
            ON texto.version = version.codigo
         WHERE version.codigo = el_codigo
           AND encode(sha256(convert_to(texto.cuerpo, 'UTF8')), 'hex')
               = version.huella_contenido
    );
$funcion$;

COMMENT ON FUNCTION didaxia_version_decidible(text) IS
    'Si esa version tiene instantanea y su sha256 coincide con la huella '
    'publicada. Informativa: la barrera real es didaxia_version_requerida() y '
    'el disparador que la consulta. Falso para una version anterior a la '
    'migracion 13, que no tiene documento y no se rellena a posteriori.';
