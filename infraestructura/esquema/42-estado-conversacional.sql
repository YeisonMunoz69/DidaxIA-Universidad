CREATE TABLE IF NOT EXISTS tutor_estado_conversacion (
    sujeto text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    conversacion text NOT NULL CHECK (btrim(conversacion) <> ''),
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
    estado jsonb NOT NULL CHECK (jsonb_typeof(estado) = 'object'),
    actualizada_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sujeto, conversacion)
);
