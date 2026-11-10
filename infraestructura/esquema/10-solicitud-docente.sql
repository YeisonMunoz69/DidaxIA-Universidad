-- ==============================================================================
-- 10-solicitud-docente.sql — Persistencia de solicitudes de rol docente · D-16 C
-- ==============================================================================
--
-- La mitad de `RegistroDeDocentes` (adaptadores/entrantes/http/docentes.py)
-- que vivía solo en memoria del proceso: la lista manual sigue en
-- `DOCENTES_AUTORIZADOS` sin cambios, esto es solo la cola de solicitud y
-- aprobación. Sin esto, una solicitud pendiente —o su historial de
-- aprobación/rechazo— desaparecía en cualquier reinicio del backend, sin
-- que quien la pidió se enterara de por qué tiene que volver a pedirla.

CREATE TABLE IF NOT EXISTS solicitud_docente (
    id       text PRIMARY KEY,
    correo   text NOT NULL,
    creada   timestamp with time zone NOT NULL DEFAULT now(),
    estado   text NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    nota     text
);

COMMENT ON TABLE solicitud_docente IS
    'Solicitudes de rol docente de D-16 opción C. Sin límite de reintentos '
    'a propósito (ver el docstring de docentes.py): una cuenta puede pedir '
    'de nuevo tras un rechazo, y eso crea una fila nueva, no reescribe esta.';

-- `es_docente()` busca por correo + estado aprobada en cada apertura de
-- sesión; `solicitar()` busca la pendiente de un correo para no duplicar.
CREATE INDEX IF NOT EXISTS solicitud_docente_correo_estado
    ON solicitud_docente (correo, estado);
