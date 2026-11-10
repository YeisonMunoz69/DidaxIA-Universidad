ALTER TABLE clase
    ADD COLUMN IF NOT EXISTS archivada_en timestamptz,
    ADD COLUMN IF NOT EXISTS archivada_por text,
    ADD COLUMN IF NOT EXISTS motivo_archivo text;

CREATE INDEX IF NOT EXISTS clase_activa_creador
    ON clase (creador) WHERE archivada_en IS NULL;
