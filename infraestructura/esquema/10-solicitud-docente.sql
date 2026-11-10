CREATE TABLE IF NOT EXISTS solicitud_docente (
    id       text PRIMARY KEY,
    correo   text NOT NULL,
    creada   timestamp with time zone NOT NULL DEFAULT now(),
    estado   text NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    nota     text
);

CREATE INDEX IF NOT EXISTS solicitud_docente_correo_estado
    ON solicitud_docente (correo, estado);
