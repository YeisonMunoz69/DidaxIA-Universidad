ALTER TABLE aclaracion_docente
    ADD COLUMN IF NOT EXISTS turno text;

CREATE INDEX IF NOT EXISTS aclaracion_docente_por_turno
    ON aclaracion_docente (estudiante, sesion, turno)
    WHERE turno IS NOT NULL;
