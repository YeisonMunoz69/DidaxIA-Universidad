\encoding UTF8

ALTER TABLE rectificacion_edad
    ADD COLUMN IF NOT EXISTS origen text NOT NULL DEFAULT 'investigacion'
    CHECK (origen IN ('investigacion', 'onboarding_estudiante', 'integracion_interna'));
