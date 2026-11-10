-- Cada republicación conserva su propio envío, respuestas y visitas por curso.
ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS envio integer
    NOT NULL DEFAULT 1 CHECK (envio > 0);
ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS revision_aviso integer
    NOT NULL DEFAULT 0 CHECK (revision_aviso >= 0);
UPDATE recurso_publicacion p SET revision_aviso=r.revision
    FROM recurso_investigacion r WHERE r.id=p.recurso AND p.revision_aviso=0;
ALTER TABLE recurso_publicacion ADD COLUMN IF NOT EXISTS estado text
    CHECK (estado IN ('publicado','cerrado','archivado'));
UPDATE recurso_publicacion p SET estado=r.estado FROM recurso_investigacion r
    WHERE r.id=p.recurso AND p.estado IS NULL;
ALTER TABLE recurso_publicacion ALTER COLUMN estado SET NOT NULL;
ALTER TABLE recurso_publicacion ALTER COLUMN estado SET DEFAULT 'publicado';
ALTER TABLE recurso_publicacion DROP CONSTRAINT IF EXISTS recurso_publicacion_recurso_clase_key;
CREATE UNIQUE INDEX IF NOT EXISTS recurso_publicacion_por_envio
    ON recurso_publicacion(recurso,envio,clase);

-- Antes sólo se conservaba la primera y última apertura: no se inventan visitas.
ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS aperturas bigint
    NOT NULL DEFAULT 1 CHECK (aperturas > 0);
ALTER TABLE recurso_visita ADD COLUMN IF NOT EXISTS conteo_completo boolean
    NOT NULL DEFAULT false;
ALTER TABLE recurso_visita ALTER COLUMN conteo_completo SET DEFAULT true;
