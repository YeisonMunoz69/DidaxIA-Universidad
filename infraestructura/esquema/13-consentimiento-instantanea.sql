\encoding UTF8
-- ---------------------------------------------------------------------------
-- 13-consentimiento-instantanea.sql · el TEXTO que se leyó, no sólo su huella
-- ---------------------------------------------------------------------------
-- El defecto que esta migración cierra, dicho por el propio árbol
-- ---------------------------------------------------------------------------
-- `DecisionConjunta.svelte` le promete a la persona:
--
--     «La huella identifica el texto exacto que estás leyendo.»
--
-- Y hasta hoy eso no era cierto. `consentimiento_version` (migración 11) guarda
-- `huella_contenido` y NO guarda el documento; `version_como_json()` lo declara
-- sin rodeos: «El texto no viaja porque no existe». Lo único que la pantalla
-- ofrecía leer eran enlaces a las páginas públicas del sitio —genéricas y
-- editables—, que no son el artefacto hasheado. El texto mostrado y el texto
-- hasheado eran dos cosas distintas, y una huella que no identifica lo leído no
-- demuestra qué se aceptó, que es lo único para lo que sirve.
--
-- Esta tabla le da al documento un sitio: inmutable, junto a su versión, y con
-- la huella calculada sobre SUS bytes.
--
-- Por qué en PostgreSQL y no en un volumen
-- ---------------------------------------------------------------------------
-- Porque `infraestructura/respaldo/custodia.py` ya enumera lo que cuesta cada
-- almacén nuevo: un respaldo real tiene que coordinar PostgreSQL, el volumen de
-- autorizaciones, el registro de turnos «y un punto coherente entre los
-- cuatro». Un quinto almacén para un texto de unas páginas habría añadido esa
-- coordinación a cambio de nada. Aquí el documento se respalda, se restaura y
-- se audita con la misma operación que su versión y las decisiones que lo
-- citan, que es justamente lo que `§9` pide demostrar.
--
-- Lo que esta migración NO hace
-- ---------------------------------------------------------------------------
-- **No publica ninguna versión ni ningún texto.** Nace vacía por el mismo
-- motivo que `consentimiento_version` en la migración 11: el texto final no
-- está aprobado y sembrar uno inventado fabricaría la autorización que este
-- esquema audita. Publicar es un acto humano con su propia herramienta, su
-- `--dry-run` y su confirmación explícita.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- consentimiento_version_texto · una instantánea por versión
-- ---------------------------------------------------------------------------
-- `version` es a la vez clave primaria y foránea: una versión tiene como mucho
-- una instantánea, y una instantánea no existe sin su versión. `ON DELETE
-- RESTRICT` como en el resto del modelo — nada de esto se borra en cascada.
--
-- `cuerpo` es el documento COMPLETO en su forma canónica, tal como lo define
-- `dominio/modelo/instantanea_consentimiento.py`: NFC, saltos LF, exactamente
-- un salto final, UTF-8. La base no vuelve a canonicalizar —no sabría hacerlo
-- igual que Python y dos criterios que puedan discrepar son peores que uno—,
-- pero sí exige lo que puede comprobar: que no venga vacío y que termine en un
-- único salto de línea. Un cuerpo con `\r` dentro delata que alguien escribió
-- sin canonicalizar, y entonces la huella publicada no sería la de estos bytes.
--
-- `medio` es un catálogo cerrado con un solo valor, por la misma razón que
-- `consentimiento_finalidad` lo es: servir un cuerpo cuyo tipo se adivina es la
-- vía corta a que un navegador lo interprete como otra cosa. Añadir un segundo
-- exige editar este archivo, es decir, una migración deliberada.
CREATE TABLE IF NOT EXISTS consentimiento_version_texto (
    version       text PRIMARY KEY
                      REFERENCES consentimiento_version (codigo) ON DELETE RESTRICT,
    cuerpo        text NOT NULL,
    medio         text NOT NULL DEFAULT 'text/markdown'
                      CHECK (medio IN ('text/markdown')),
    registrada_en timestamp with time zone NOT NULL DEFAULT now(),
    -- Las tres cosas que la base puede comprobar de la forma canónica sin
    -- reimplementarla: que hay documento, que termina en un único salto y que
    -- no quedó ningún retorno de carro dentro.
    CONSTRAINT consentimiento_version_texto_no_vacio
        CHECK (btrim(cuerpo) <> ''),
    CONSTRAINT consentimiento_version_texto_salto_final
        CHECK (cuerpo LIKE E'%\n' AND cuerpo NOT LIKE E'%\n\n'),
    CONSTRAINT consentimiento_version_texto_sin_retorno
        CHECK (position(E'\r' in cuerpo) = 0)
);

COMMENT ON TABLE consentimiento_version_texto IS
    'Instantanea canonica e inmutable del documento de cada version: el texto '
    'EXACTO sobre cuyos bytes se calculo huella_contenido. Nace vacia; el '
    'texto final no esta aprobado y publicarlo es un acto humano aparte. Sin '
    'esta tabla la huella no identificaba lo que la persona leia.';

COMMENT ON COLUMN consentimiento_version_texto.cuerpo IS
    'Documento completo en forma canonica (NFC, saltos LF, un unico salto '
    'final, UTF-8) segun dominio/modelo/instantanea_consentimiento.py. Es el '
    'artefacto que se sirve para leer y sobre el que se calcula el SHA-256.';

-- --- inmutabilidad ---------------------------------------------------------
-- La misma disciplina que la migración 11 aplica a versiones y eventos, y por
-- el mismo motivo: si la conexión de la aplicación puede reescribir el cuerpo,
-- entonces la huella deja de probar qué leyó quien aceptó — bastaría editar el
-- texto para que la prueba apuntara a otro documento.
--
-- ⚠️ Y aquí importa más que en ninguna otra tabla del modelo. Una versión
-- publicada no se edita (`§8.5`): cambiar una coma exige publicar otro código.
-- Este disparador es lo que hace que esa regla sea una propiedad de la base y
-- no una costumbre de quien escriba la siguiente consulta.
--
-- Reutiliza `didaxia_rechazar_modificacion()`, que la migración 11 ya define.
-- No se redefine aquí: dos copias de la misma función podrían divergir, y la
-- que quedara vieja dejaría una tabla editable sin que nada lo dijera.
CREATE OR REPLACE TRIGGER consentimiento_version_texto_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version_texto
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
