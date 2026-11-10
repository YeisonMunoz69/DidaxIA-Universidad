\encoding UTF8

BEGIN;

ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS contexto_de_uso text NOT NULL
        DEFAULT 'aprendizaje_estudiante'
        CHECK (contexto_de_uso IN ('aprendizaje_estudiante', 'consulta_profesional'));

ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS contexto_de_uso text NOT NULL
        DEFAULT 'aprendizaje_estudiante'
        CHECK (contexto_de_uso IN ('aprendizaje_estudiante', 'consulta_profesional'));

COMMIT;
