CREATE TABLE IF NOT EXISTS analisis_conductual (
    historial bigint NOT NULL REFERENCES historial_turno(id) ON DELETE CASCADE,
    version text NOT NULL CHECK (version <> ''),
    modelo text NOT NULL,
    huella text NOT NULL CHECK (length(huella) = 64),
    origen text NOT NULL CHECK (origen IN ('turno', 'relectura')),
    lectura jsonb NOT NULL CHECK (jsonb_typeof(lectura) = 'object'),
    trazas_matematicas jsonb NOT NULL CHECK (jsonb_typeof(trazas_matematicas) = 'array'),
    analizado_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (historial, version)
);
