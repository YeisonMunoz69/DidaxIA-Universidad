-- Conserva la clase y su evidencia, pero permite retirarla del producto y KPI.
ALTER TABLE clase
    ADD COLUMN IF NOT EXISTS archivada_en timestamptz,
    ADD COLUMN IF NOT EXISTS archivada_por text,
    ADD COLUMN IF NOT EXISTS motivo_archivo text;

COMMENT ON COLUMN clase.archivada_en IS
    'Una clase archivada no recibe matrículas nuevas ni integra los KPI; su historial permanece para auditoría.';

CREATE INDEX IF NOT EXISTS clase_activa_creador
    ON clase (creador) WHERE archivada_en IS NULL;
