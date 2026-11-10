-- 21-aclaracion-anclada.sql · la corrección docente conserva su turno

-- Aditiva y sin inferencias retrospectivas. Las aclaraciones anteriores se
-- dejan en NULL: atribuirlas al turno más cercano por fecha podría enlazarlas
-- con una respuesta distinta si el docente revisó la cola más tarde.
ALTER TABLE aclaracion_docente
    ADD COLUMN IF NOT EXISTS turno text;

CREATE INDEX IF NOT EXISTS aclaracion_docente_por_turno
    ON aclaracion_docente (estudiante, sesion, turno)
    WHERE turno IS NOT NULL;

COMMENT ON COLUMN aclaracion_docente.turno IS
    'Identificador estable de CuerpoTurno.turno. NULL sólo en aclaraciones históricas que no se pueden atribuir sin inventar.';
