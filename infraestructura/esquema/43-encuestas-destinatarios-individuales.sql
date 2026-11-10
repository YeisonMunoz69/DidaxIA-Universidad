-- Retirar invitaciones sin borrar visitas, ni cambiar contenido o envío.
ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS retirada_en timestamptz;
ALTER TABLE recurso_publicacion DROP CONSTRAINT IF EXISTS recurso_publicacion_audiencia_check;
ALTER TABLE recurso_publicacion ADD CONSTRAINT recurso_publicacion_audiencia_check
    CHECK (audiencia IN ('estudiantes','docentes','individuales'));
ALTER TABLE recurso_publicacion DROP CONSTRAINT IF EXISTS recurso_publicacion_destino;
ALTER TABLE recurso_publicacion ADD CONSTRAINT recurso_publicacion_destino CHECK (
    (audiencia='estudiantes' AND clase IS NOT NULL AND destinatario IS NULL) OR
    (audiencia IN ('docentes','individuales') AND clase IS NULL AND destinatario IS NOT NULL));
