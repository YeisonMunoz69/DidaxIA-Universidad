ALTER TABLE recurso_investigacion ADD COLUMN IF NOT EXISTS es_plantilla boolean NOT NULL DEFAULT false;

ALTER TABLE recurso_publicacion ALTER COLUMN clase DROP NOT NULL;

ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS destinatario text REFERENCES persona(sujeto_google) ON DELETE CASCADE;

ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS audiencia text NOT NULL DEFAULT 'estudiantes'
    CHECK (audiencia IN ('estudiantes','docentes'));

ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS cerrada_en timestamptz;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='recurso_publicacion_destino' AND conrelid='recurso_publicacion'::regclass) THEN
        ALTER TABLE recurso_publicacion ADD CONSTRAINT recurso_publicacion_destino CHECK (
            (audiencia='estudiantes' AND clase IS NOT NULL AND destinatario IS NULL) OR
            (audiencia='docentes' AND clase IS NULL AND destinatario IS NOT NULL));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS recurso_publicacion_docente_envio ON recurso_publicacion(recurso,envio,destinatario);

ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS actividad_en timestamptz;

ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS gracia_hasta timestamptz;

CREATE INDEX IF NOT EXISTS recurso_publicacion_destinatario ON recurso_publicacion(destinatario);
