-- Estado operativo del tutor: aislado por titular e hilo, con revisión explícita.
CREATE TABLE IF NOT EXISTS tutor_estado_conversacion (
    sujeto text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    conversacion text NOT NULL CHECK (btrim(conversacion) <> ''),
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
    estado jsonb NOT NULL CHECK (jsonb_typeof(estado) = 'object'),
    actualizada_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sujeto, conversacion)
);
COMMENT ON TABLE tutor_estado_conversacion IS
    'Continuidad operativa; no es evaluación longitudinal. Se suprime con el titular o su conversación.';
