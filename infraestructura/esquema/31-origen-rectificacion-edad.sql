\encoding UTF8
-- 31-origen-rectificacion-edad.sql · procedencia explícita de la rectificación
-- ============================================================================
-- La tabla histórica ya conservaba actor, motivo, fecha, valores y efectos.
-- Esta columna distingue la rectificación gobernada por investigación de la
-- autocorrección que el estudiante hace antes de una matrícula aprobada.

ALTER TABLE rectificacion_edad
    ADD COLUMN IF NOT EXISTS origen text NOT NULL DEFAULT 'investigacion'
    CHECK (origen IN ('investigacion', 'onboarding_estudiante', 'integracion_interna'));

COMMENT ON COLUMN rectificacion_edad.origen IS
    'Procedencia del acto: vía profesional gobernada, autocorrección previa a la vinculación o integración interna.';
