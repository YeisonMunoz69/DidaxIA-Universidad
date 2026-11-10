-- Una matrícula vigente por estudiante; solicitudes y decisiones trazables.
-- No se elige automáticamente entre matrículas preexistentes ni se atribuye
-- una clase a turnos antiguos. Resolver duplicados exige una decisión humana.
BEGIN;

LOCK TABLE clase_matricula IN SHARE ROW EXCLUSIVE MODE;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM clase_matricula GROUP BY identificador HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Migración 18 detenida: existen estudiantes con varias matrículas vigentes. Resolver explícitamente antes de continuar; no se modificó ninguna matrícula.';
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS clase_matricula_unica_vigente
    ON clase_matricula (identificador);

CREATE TABLE IF NOT EXISTS clase_solicitud (
    id text PRIMARY KEY,
    estudiante text NOT NULL,
    clase_destino text NOT NULL REFERENCES clase(id) ON DELETE CASCADE,
    clase_origen text REFERENCES clase(id) ON DELETE SET NULL,
    estado text NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aprobada', 'rechazada', 'cancelada')),
    creada_en timestamptz NOT NULL DEFAULT clock_timestamp(),
    resuelta_en timestamptz,
    resuelta_por text,
    CHECK ((estado = 'pendiente' AND resuelta_en IS NULL AND resuelta_por IS NULL)
        OR (estado <> 'pendiente' AND resuelta_en IS NOT NULL AND resuelta_por IS NOT NULL)),
    CHECK (resuelta_en IS NULL OR resuelta_en >= creada_en)
);
CREATE UNIQUE INDEX IF NOT EXISTS clase_solicitud_pendiente
    ON clase_solicitud (estudiante) WHERE estado = 'pendiente';
CREATE INDEX IF NOT EXISTS clase_solicitud_destino
    ON clase_solicitud (clase_destino, creada_en);

CREATE TABLE IF NOT EXISTS clase_solicitud_evento (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    solicitud text NOT NULL REFERENCES clase_solicitud(id) ON DELETE CASCADE,
    actor text NOT NULL,
    rol_actor text NOT NULL CHECK (rol_actor IN ('estudiante', 'docente', 'investigador')),
    estado text NOT NULL CHECK (estado IN ('pendiente', 'aprobada', 'rechazada', 'cancelada')),
    momento timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (solicitud, estado)
);

CREATE TABLE IF NOT EXISTS clase_matricula_historial (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estudiante text NOT NULL,
    clase text NOT NULL REFERENCES clase(id) ON DELETE CASCADE,
    desde timestamptz NOT NULL,
    hasta timestamptz,
    solicitud text REFERENCES clase_solicitud(id) ON DELETE SET NULL,
    procedencia text NOT NULL CHECK (procedencia IN ('preexistente', 'aprobacion')),
    CHECK (hasta IS NULL OR hasta >= desde)
);
CREATE UNIQUE INDEX IF NOT EXISTS clase_historial_unico_vigente
    ON clase_matricula_historial(estudiante) WHERE hasta IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS clase_historial_solicitud
    ON clase_matricula_historial(solicitud) WHERE solicitud IS NOT NULL;

-- Conserva el dato conocido de la matrícula existente. No inventa aprobación
-- ni interpreta esta fila como prueba de la clase de una conversación antigua.
INSERT INTO clase_matricula_historial (estudiante, clase, desde, procedencia)
SELECT m.identificador, m.clase, m.desde, 'preexistente'
  FROM clase_matricula m
 WHERE NOT EXISTS (
     SELECT 1 FROM clase_matricula_historial h WHERE h.estudiante = m.identificador
 );

COMMIT;
