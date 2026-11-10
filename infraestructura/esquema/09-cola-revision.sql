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

CREATE INDEX IF NOT EXISTS cola_revision_pendientes
    ON cola_revision (estado, recibido)
    WHERE estado = 'pendiente';
