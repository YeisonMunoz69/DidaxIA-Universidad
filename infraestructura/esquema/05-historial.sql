\encoding UTF8

BEGIN;

CREATE TABLE IF NOT EXISTS historial_turno (

    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    turno                text NOT NULL CHECK (btrim(turno) <> ''),

    identificador_sesion text NOT NULL CHECK (btrim(identificador_sesion) <> ''),

    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    momento              timestamptz NOT NULL DEFAULT now(),

    autor                text NOT NULL CHECK (autor IN ('estudiante', 'sistema')),

    contenido            text NOT NULL CHECK (btrim(contenido) <> ''),

    degradado            boolean NOT NULL DEFAULT false
                         CHECK (NOT degradado OR autor = 'sistema')
);

CREATE INDEX IF NOT EXISTS historial_turno_por_sujeto
    ON historial_turno (identificador_sujeto, momento DESC);

CREATE INDEX IF NOT EXISTS historial_turno_por_sesion
    ON historial_turno (identificador_sesion, id);

COMMIT;
