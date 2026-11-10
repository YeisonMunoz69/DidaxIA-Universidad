-- Preferencias visuales de la cuenta; ninguna medida educativa ni texto del chat.
CREATE TABLE IF NOT EXISTS preferencia_interfaz (
    sujeto_google text PRIMARY KEY REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    preferencias jsonb NOT NULL CHECK (jsonb_typeof(preferencias) = 'object'),
    revision integer NOT NULL DEFAULT 0 CHECK (revision >= 0),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE preferencia_interfaz IS 'Colores, tema, lectura y movimiento elegidos por el titular.';
