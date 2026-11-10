\encoding UTF8

BEGIN;

CREATE TABLE IF NOT EXISTS historial_concepto (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,
    orden       integer NOT NULL CHECK (orden >= 0),
    concepto    text NOT NULL CHECK (concepto ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    UNIQUE (historial, orden),
    UNIQUE (historial, concepto)
);

CREATE INDEX IF NOT EXISTS historial_concepto_por_mensaje
    ON historial_concepto (historial);

CREATE INDEX IF NOT EXISTS historial_concepto_por_concepto
    ON historial_concepto (concepto, historial);

CREATE TABLE IF NOT EXISTS incidencia_telemetria (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registrado_en        timestamptz NOT NULL DEFAULT now(),
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),
    clase                text CHECK (clase IS NULL OR clase ~ '^[A-Za-z0-9:._~-]{1,128}$'),
    tipo                 text NOT NULL CHECK (length(tipo) BETWEEN 1 AND 64),
    categoria            text NOT NULL CHECK (categoria IN (
                             'duplicado', 'conflicto_idempotencia', 'incompatible'
                         )),
    codigo               text NOT NULL CHECK (codigo ~ '^[a-z0-9._-]{1,64}$'),
    huella_clave         char(64) NOT NULL CHECK (huella_clave ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS incidencia_telemetria_por_sujeto
    ON incidencia_telemetria (identificador_sujeto, registrado_en DESC);

CREATE INDEX IF NOT EXISTS incidencia_telemetria_por_categoria
    ON incidencia_telemetria (categoria, registrado_en);

COMMIT;
