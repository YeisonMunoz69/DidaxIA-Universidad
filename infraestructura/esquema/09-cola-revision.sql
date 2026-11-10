-- ==============================================================================
-- 09-cola-revision.sql — Persistencia de la cola de revisión docente · RU-12
-- ==============================================================================
--
-- Hasta hoy `ColaDeRevision` (adaptadores/entrantes/http/supervision.py)
-- vivía solo en memoria del proceso: un reinicio del backend borraba
-- cualquier turno pendiente de revisión, sin que la docente que lo dejó a
-- medias se enterara. `turno` es JSONB porque `ItemDeRevision.turno` ya es
-- un `dict` de forma libre en el código de hoy — la misma razón por la que
-- `historial_bloque` no intenta tipar cada campo del bloque.

CREATE TABLE IF NOT EXISTS cola_revision (
    id                    text PRIMARY KEY,
    recibido              timestamp with time zone NOT NULL DEFAULT now(),
    urgencia              text NOT NULL,
    clase                 text,
    tipo                  text NOT NULL CHECK (tipo IN ('respuesta', 'sin-fuente', 'degradado')),
    mensaje               text NOT NULL,
    turno                 jsonb NOT NULL,
    estado                text NOT NULL DEFAULT 'pendiente'
                              CHECK (estado IN ('pendiente', 'aprobado', 'editado', 'rechazado')),
    concepcion_candidata  text,
    ansiedad_estimada     double precision
);

COMMENT ON TABLE cola_revision IS
    'Ítems de RU-12 a la espera de revisión docente, o ya resueltos. '
    '`estado` no vuelve de aprobado/editado/rechazado a pendiente — la '
    'misma disciplina de tres acciones distintas que ColaDeRevision.rechazar() '
    'ya impone en código.';

-- `listar_pendientes()` siempre filtra por estado, y casi siempre además por
-- clase o por tipo — este índice cubre el filtro más común sin tener que
-- escanear cada fila resuelta desde el principio de los tiempos.
CREATE INDEX IF NOT EXISTS cola_revision_pendientes
    ON cola_revision (estado, recibido)
    WHERE estado = 'pendiente';
