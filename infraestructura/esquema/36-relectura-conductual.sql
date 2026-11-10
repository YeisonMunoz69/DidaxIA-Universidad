-- Trabajos acotados y confirmados; no contienen mensajes de estudiantes.
CREATE TABLE IF NOT EXISTS relectura_conductual_trabajo (
    id uuid PRIMARY KEY,
    actor text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    version text NOT NULL,
    clase text,
    desde timestamptz NOT NULL,
    hasta timestamptz NOT NULL CHECK (hasta > desde),
    maximo_llamadas integer CHECK (maximo_llamadas BETWEEN 1 AND 200),
    estado text NOT NULL CHECK (estado IN (
        'vista_previa', 'en_cola', 'en_curso', 'completado', 'interrumpido'
    )),
    resumen jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(resumen) = 'object'),
    motivo text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS relectura_conductual_un_activo
    ON relectura_conductual_trabajo ((1)) WHERE estado IN ('en_cola', 'en_curso');
CREATE INDEX IF NOT EXISTS relectura_conductual_actor
    ON relectura_conductual_trabajo (actor, creado_en DESC);
COMMENT ON TABLE relectura_conductual_trabajo IS
    'Vista previa, confirmación y progreso sin contenido; la lectura sigue en analisis_conductual.';
