ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS revision_vista integer
    NOT NULL DEFAULT 0 CHECK (revision_vista >= 0);
