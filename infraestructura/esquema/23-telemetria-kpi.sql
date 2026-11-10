BEGIN;

CREATE TABLE IF NOT EXISTS evento_telemetria (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    clave_idempotencia   text NOT NULL UNIQUE
                         CHECK (clave_idempotencia ~ '^[A-Za-z0-9:._~-]{8,160}$'),

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

    origen               text NOT NULL CHECK (origen IN ('backend', 'interfaz')),

    ocurrido_en          timestamptz NOT NULL,

    registrado_en        timestamptz NOT NULL DEFAULT now(),

    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    contexto_de_uso      text NOT NULL DEFAULT 'aprendizaje_estudiante'
                         CHECK (contexto_de_uso IN (
                             'aprendizaje_estudiante', 'consulta_profesional'
                         )),

    clase                text CHECK (clase IS NULL OR clase ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    conversacion         text CHECK (conversacion IS NULL OR conversacion ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    turno                text CHECK (turno IS NULL OR turno ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    concepto             text CHECK (concepto IS NULL OR concepto ~ '^[A-Za-z0-9:._~-]{1,128}$'),

    version_corpus       text NOT NULL DEFAULT '' CHECK (length(version_corpus) <= 64),
    version_modelo       text NOT NULL DEFAULT '' CHECK (length(version_modelo) <= 64),

    metadatos            jsonb NOT NULL DEFAULT '{}'::jsonb
                         CHECK (jsonb_typeof(metadatos) = 'object'
                                AND length(metadatos::text) <= 1000)
);

CREATE INDEX IF NOT EXISTS evento_telemetria_por_tipo
    ON evento_telemetria (tipo, ocurrido_en);

CREATE INDEX IF NOT EXISTS evento_telemetria_por_sujeto
    ON evento_telemetria (identificador_sujeto, ocurrido_en DESC);

CREATE INDEX IF NOT EXISTS evento_telemetria_por_clase
    ON evento_telemetria (clase, ocurrido_en)
    WHERE clase IS NOT NULL;

CREATE INDEX IF NOT EXISTS evento_telemetria_por_versiones
    ON evento_telemetria (ocurrido_en)
    WHERE tipo = 'turno.respondido';

CREATE OR REPLACE FUNCTION didaxia_rechazar_actualizacion() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
BEGIN
    RAISE EXCEPTION 'fila append-only: un hecho historico no se corrige, se registra otro'
        USING ERRCODE = 'check_violation',
              HINT = 'el DELETE si esta permitido: lo necesita la supresion de EQ-022';
    RETURN NULL;
END;
$funcion$;

CREATE OR REPLACE TRIGGER evento_telemetria_append_only
    BEFORE UPDATE ON evento_telemetria
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_actualizacion();

COMMIT;
