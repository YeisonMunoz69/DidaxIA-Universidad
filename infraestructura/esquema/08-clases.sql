-- ==============================================================================
-- 08-clases.sql — Persistencia de clases y matrícula en BD · DD-12 · PM-B24
-- ==============================================================================
--
-- Hasta hoy `Clases` (adaptadores/entrantes/http/clases.py) vivía solo en
-- memoria del proceso. Un curso creado por un docente, o la matrícula de un
-- estudiante, desaparecía en cualquier reinicio del backend — sin que nada lo
-- recuperara. Este esquema es lo que AdaptadorClasesPostgres
-- (adaptadores/salientes/registro/clases_db.py) usa cuando AGENTE_BD está
-- configurada; sin ella, el sistema sigue cayendo al almacén en memoria, tal
-- como hace hoy con el resto de piezas que dependen de la base.

CREATE TABLE IF NOT EXISTS clase (
    id         text PRIMARY KEY,
    nombre     text NOT NULL,
    creador    text NOT NULL,
    codigo     text NOT NULL UNIQUE,
    creada_en  timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE clase IS
    'Una clase de DD-12: quién la creó, con qué código se comparte.';

CREATE INDEX IF NOT EXISTS clase_creador
    ON clase (creador);

-- Una fila por matrícula. La clave primaria compuesta es lo que hace que
-- «unirse dos veces no duplica la matrícula» sea una propiedad de la base
-- (INSERT ... ON CONFLICT DO NOTHING) y no solo del código Python de encima.
CREATE TABLE IF NOT EXISTS clase_matricula (
    clase          text NOT NULL REFERENCES clase (id) ON DELETE CASCADE,
    identificador  text NOT NULL,
    desde          timestamp with time zone NOT NULL DEFAULT now(),
    PRIMARY KEY (clase, identificador)
);

COMMENT ON TABLE clase_matricula IS
    'Quién está en qué clase. `identificador` es sujeto_de(datos) — la '
    'identidad estable cuando la sesión se autenticó con Google, la de '
    'sesión si no. Ver adaptadores/entrantes/http/sesiones.py::sujeto_de().';

-- La consulta de RD-22 (suprimir_sujeto) y la de «mis clases» (mias) buscan
-- las dos por `identificador`, nunca por `clase` sola — este es el índice
-- que las dos necesitan.
CREATE INDEX IF NOT EXISTS clase_matricula_identificador
    ON clase_matricula (identificador);
