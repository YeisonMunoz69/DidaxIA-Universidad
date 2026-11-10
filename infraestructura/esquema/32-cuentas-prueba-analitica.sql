\encoding UTF8
-- 32-cuentas-prueba-analitica.sql · exclusión explícita de analítica
-- ============================================================================
-- Una cuenta técnica o de ensayo puede usar una clase real sin que su actividad
-- deba confundirse con participación estudiantil. El marcador nace en falso: no
-- infiere la condición desde el correo, el nombre o el comportamiento y por eso
-- no excluye silenciosamente a una persona real.

ALTER TABLE persona
    ADD COLUMN IF NOT EXISTS es_cuenta_prueba boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN persona.es_cuenta_prueba IS
    'Excluye explícitamente la cuenta de tableros y analítica; no se infiere de nombre, correo ni actividad.';
