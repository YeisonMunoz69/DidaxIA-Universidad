ALTER TABLE clase
    ADD COLUMN IF NOT EXISTS unidad_curricular text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS notacion_curricular text NOT NULL DEFAULT 'sen',
    ADD COLUMN IF NOT EXISTS observaciones_curriculares text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS contexto_actualizado_en timestamp with time zone;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'clase_notacion_curricular_valida'
    ) THEN
        ALTER TABLE clase ADD CONSTRAINT clase_notacion_curricular_valida
            CHECK (notacion_curricular IN ('sen', 'sin'));
    END IF;
END
$$;
