-- Cada estudiante reconoce la revisión que abrió. Publicar o cerrar actualiza
-- la revisión; el contador señala cambios nuevos, no encuestas sin responder.
ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS revision_vista integer
    NOT NULL DEFAULT 0 CHECK (revision_vista >= 0);
