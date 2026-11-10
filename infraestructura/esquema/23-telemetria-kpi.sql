-- ==============================================================================
-- 23-telemetria-kpi.sql — Eventos históricos para el catálogo KPI v1.1
-- ==============================================================================
--
-- El número 23 sale de `infraestructura/migraciones/catalogo.py::descubrir()`,
-- que exige una secuencia contigua y termina hoy en `22-oferta-academica.sql`.
-- No se supuso: se comprobó antes de escribir este archivo.
--
-- QUÉ FALTABA Y POR QUÉ HACE FALTA UNA TABLA
-- ------------------------------------------------------------------------
-- La Fase 8 pide medir cosas que hoy **nadie registra**: qué versión de corpus
-- y de modelo respondió de verdad un turno, cuándo se derivó a supervisión,
-- cuándo se actualizó el contexto curricular, y —desde el navegador— cuándo se
-- abrió el panel de fuentes o se exportó una gráfica.
--
-- Ninguna tabla existente sirve para eso, y se miraron las tres candidatas:
--
--   · `historial_turno` es la conversación. Añadirle columnas de instrumentación
--     mezclaría el hecho pedagógico con la medición, y su cascada de supresión
--     borra el turno entero: perderíamos el agregado al ejercer un derecho.
--   · `registro_turno` es la fila de referencia del registro forense, con una
--     fila por turno y clave primaria `turno`. Un turno produce varios eventos.
--   · `auditoria_operacion` es la constancia de operaciones administrativas
--     (`EQ-023`), es inmutable frente a UPDATE **y DELETE**, y su `detalle` está
--     declarado como «identificadores y conteos». Meter aquí la telemetría de
--     uso de estudiantes convertiría la tabla que más sobrevive en la que más
--     datos de uso conserva, justo al revés de lo que su cabecera decide.
--
-- `auditoria_operacion` SÍ se reutiliza para lo que es suyo: cada lectura
-- institucional de KPI se anota allí con `anotar()`, en la misma transacción.
-- Esta tabla es otra cosa: el hecho medido, no la consulta de quien lo mira.
--
-- APPEND-ONLY, PERO NO INMUTABLE
-- ------------------------------------------------------------------------
-- El disparador de abajo rechaza **UPDATE** y no DELETE, y la diferencia es
-- deliberada. `EQ-022` obliga a que una supresión procedente alcance los datos
-- de la persona, y estas filas describen su uso: son suyas. El modelo correcto
-- es el de `historial_turno` —que tampoco lleva disparador de inmutabilidad y sí
-- tiene borrado por sujeto—, no el de `auditoria_operacion`, que sobrevive a la
-- supresión porque es la prueba de que la supresión ocurrió.
--
-- Un hecho histórico no se corrige: se registra otro. Eso es lo que impide el
-- UPDATE, y es lo que hace que un recuento del pasado no cambie al releerlo.
--
-- IDEMPOTENCIA
-- ------------------------------------------------------------------------
-- `clave_idempotencia` es única y la pone el emisor. El adaptador inserta con
-- `ON CONFLICT DO NOTHING`, así que un reintento —del navegador que no recibió
-- la respuesta, o del backend tras un fallo de red— no crea una segunda fila.
-- Sin esto, «apertura de fuentes» contaría dos veces lo que ocurrió una.
--
-- LO QUE ESTA TABLA NO GUARDA
-- ------------------------------------------------------------------------
-- Ni texto de conversación, ni correo, ni nombre. La fuente canónica de la
-- conversación es `historial_turno` y no se duplica aquí: estas filas llevan
-- identificadores, versiones y metadatos cerrados. Los CHECK de longitud de
-- `metadatos` y de las referencias son la mitad SQL de esa regla; la otra
-- mitad la aplica `dominio/modelo/telemetria.py`, que valida vocabulario,
-- esquema, propiedad y forma antes de llegar aquí.
--
-- IDEMPOTENTE Y SIN PURGA: tabla nueva con IF NOT EXISTS, índices con IF NOT
-- EXISTS y una función y un disparador con CREATE OR REPLACE. No borra nada y
-- no toca ninguna columna existente. Aplicarlo dos veces no cambia nada.

BEGIN;

CREATE TABLE IF NOT EXISTS evento_telemetria (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- ⚠️ LA COLUMNA POR LA QUE UN REINTENTO NO DUPLICA. La pone el emisor,
    -- porque el reintento también es suyo: si la generara el servidor, el
    -- segundo intento del mismo hecho sería una fila nueva.
    clave_idempotencia   text NOT NULL UNIQUE
                         CHECK (clave_idempotencia ~ '^[A-Za-z0-9:._~-]{8,160}$'),

    -- El vocabulario cerrado. La lista es la misma que `TipoDeEvento` en
    -- `dominio/modelo/telemetria.py`, y una prueba las compara para que no
    -- diverjan: un tipo nuevo en Python sin su valor aquí produciría un fallo
    -- de restricción en producción y no en la suite.
    tipo                 text NOT NULL CHECK (tipo IN (
                             'turno.enviado',
                             'turno.respondido',
                             'supervision.derivada',
                             'supervision.decidida',
                             'curricular.actualizado',
                             'fuentes.abiertas',
                             'respuesta.copiada',
                             'grafica.generada',
                             'grafica.abierta',
                             'grafica.interaccion',
                             'grafica.rango_cambiado',
                             'grafica.exportada',
                             'supervision.abierta',
                             'informe.generado',
                             'informe.descargado',
                             'autocorreccion.detectada',
                             'autocorreccion.confirmada'
                         )),

    -- Quién declaró el hecho. Lo decide el tipo, no quien envía; el dominio lo
    -- impone y esta columna lo conserva para poder auditar la procedencia de
    -- una serie sin volver a mirar el código de entonces.
    origen               text NOT NULL CHECK (origen IN ('backend', 'interfaz')),

    -- Cuándo ocurrió, con zona. Es lo que ordena la serie.
    ocurrido_en          timestamptz NOT NULL,

    -- Cuándo llegó. Las dos y no una: su diferencia es el «retraso de
    -- telemetría» que la superficie de calidad de datos necesita, y con una
    -- sola columna ese retraso sería inobservable.
    registrado_en        timestamptz NOT NULL DEFAULT now(),

    -- Se llama igual que en `historial_turno` y `registro_turno` a propósito:
    -- es la clave por la que `inventario_db.py` cuenta lo que una supresión
    -- alcanzaría, y un nombre distinto habría exigido un caso especial allí.
    --
    -- Sin clave foránea a `persona`, por el mismo motivo que `historial_turno`:
    -- una referencia con ON DELETE RESTRICT convertiría a esta tabla en un
    -- obstáculo para la supresión que tiene que poder alcanzarla.
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    -- `EQ-031` · el uso profesional se registra y no se agrega. Se guarda el
    -- contexto en la fila para poder excluirla de todo KPI sin volver a
    -- preguntar por el rol de nadie, que un rol revocable no puede contestar
    -- hacia atrás. Mismo valor y mismo CHECK que la migración 17.
    contexto_de_uso      text NOT NULL DEFAULT 'aprendizaje_estudiante'
                         CHECK (contexto_de_uso IN (
                             'aprendizaje_estudiante', 'consulta_profesional'
                         )),

    -- Las cuatro referencias del encargo: clase, conversación, turno y
    -- concepto. Todas admiten NULL —hay eventos que no pertenecen a una clase—
    -- y ninguna admite la cadena vacía, que sería una segunda forma de decir
    -- «no consta» y obligaría a los agregados a acordarse de las dos.
    --
    -- Sin clave foránea a `clase`: un hecho histórico no puede perder su clase
    -- por un ON DELETE SET NULL, que además sería un UPDATE sobre una fila
    -- append-only. La existencia y la propiedad de la clase las comprueba el
    -- adaptador dentro de la misma transacción en la que escribe.
    clase                text CHECK (clase IS NULL OR clase ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    conversacion         text CHECK (conversacion IS NULL OR conversacion ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    turno                text CHECK (turno IS NULL OR turno ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    concepto             text CHECK (concepto IS NULL OR concepto ~ '^[A-Za-z0-9:._~-]{1,128}$'),

    -- Las dos versiones que el encargo pide y que hasta hoy no se persistían.
    -- Cadena vacía es «no consta»: son columnas NOT NULL con DEFAULT '' porque
    -- casi ningún tipo de evento las lleva, y un NULL habría exigido COALESCE
    -- en cada agregado.
    version_corpus       text NOT NULL DEFAULT '' CHECK (length(version_corpus) <= 64),
    version_modelo       text NOT NULL DEFAULT '' CHECK (length(version_modelo) <= 64),

    -- Metadatos cerrados por tipo. El objeto lo valida el dominio; aquí se
    -- exige que sea un objeto y que quepa en una fila pequeña. El tope de 1000
    -- caracteres es la barrera SQL contra el uso que hay que impedir: volcar
    -- aquí el texto de una respuesta.
    metadatos            jsonb NOT NULL DEFAULT '{}'::jsonb
                         CHECK (jsonb_typeof(metadatos) = 'object'
                                AND length(metadatos::text) <= 1000)
);

COMMENT ON TABLE evento_telemetria IS
    'Fase 8: hechos historicos que alimentan el catalogo KPI v1.1. Append-only '
    '(sin UPDATE) e idempotente por clave_idempotencia. No guarda texto de '
    'conversacion, correos ni nombres: la fuente canonica de la conversacion es '
    'historial_turno.';

COMMENT ON COLUMN evento_telemetria.clave_idempotencia IS
    'La pone el emisor. ON CONFLICT DO NOTHING convierte un reintento en un no-op.';

COMMENT ON COLUMN evento_telemetria.registrado_en IS
    'Cuando llego. Su diferencia con ocurrido_en es el retraso de telemetria.';

COMMENT ON COLUMN evento_telemetria.contexto_de_uso IS
    'EQ-031: consulta_profesional se registra y queda fuera de todo KPI.';

-- «Cuántos eventos de este tipo hubo en este periodo» es la consulta de casi
-- todos los indicadores de la Fase 8.
CREATE INDEX IF NOT EXISTS evento_telemetria_por_tipo
    ON evento_telemetria (tipo, ocurrido_en);

-- La clave de supresión y la de la ficha individual, igual que en
-- `historial_turno_por_sujeto`. El mismo índice sirve a las dos.
CREATE INDEX IF NOT EXISTS evento_telemetria_por_sujeto
    ON evento_telemetria (identificador_sujeto, ocurrido_en DESC);

-- El alcance del docente y el de una comparación institucional por curso.
-- Parcial porque un evento sin clase no se busca nunca por clase, y el índice
-- completo habría indexado también esas filas para nada.
CREATE INDEX IF NOT EXISTS evento_telemetria_por_clase
    ON evento_telemetria (clase, ocurrido_en)
    WHERE clase IS NOT NULL;

-- «Qué versiones de corpus y de modelo respondieron en este periodo», que son
-- dos indicadores de la dimensión F y no tenían de dónde salir.
CREATE INDEX IF NOT EXISTS evento_telemetria_por_versiones
    ON evento_telemetria (ocurrido_en)
    WHERE tipo = 'turno.respondido';

-- ---------------------------------------------------------------------------
-- Append-only: sin UPDATE, con DELETE
-- ---------------------------------------------------------------------------
-- Una función propia y no `didaxia_rechazar_modificacion()` de la migración 11,
-- porque aquélla rechaza UPDATE **y** DELETE y su mensaje habla de la supresión
-- de `EQ-022` como de un camino aparte. Aquí el DELETE es justamente el camino
-- que tiene que quedar abierto: estas filas describen el uso de una persona y
-- una supresión procedente debe alcanzarlas.
--
-- Reutilizar aquella función habría dejado el mensaje equivocado en el error, y
-- un mensaje equivocado en una restricción se convierte en una hora perdida el
-- día que alguien lo lea de madrugada.
CREATE OR REPLACE FUNCTION didaxia_rechazar_actualizacion() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
BEGIN
    RAISE EXCEPTION 'fila append-only: un hecho historico no se corrige, se registra otro'
        USING ERRCODE = 'check_violation',
              HINT = 'el DELETE si esta permitido: lo necesita la supresion de EQ-022';
    RETURN NULL;
END;
$funcion$;

COMMENT ON FUNCTION didaxia_rechazar_actualizacion() IS
    'Append-only sin inmutabilidad: rechaza UPDATE y deja pasar DELETE, para que '
    'una supresion procedente pueda alcanzar los datos de uso de una persona.';

CREATE OR REPLACE TRIGGER evento_telemetria_append_only
    BEFORE UPDATE ON evento_telemetria
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_actualizacion();

COMMIT;
