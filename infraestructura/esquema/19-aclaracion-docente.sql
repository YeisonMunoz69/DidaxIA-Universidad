-- 19-aclaracion-docente.sql · correcciones visibles y auditables de supervisión

-- La cola histórica no sabía a qué estudiante ni a qué conversación pertenecía
-- un elemento. Las columnas son anulables para conservar los ítems anteriores,
-- que no se pueden atribuir retrospectivamente sin inventar datos.
ALTER TABLE cola_revision
    ADD COLUMN IF NOT EXISTS estudiante text,
    ADD COLUMN IF NOT EXISTS sesion text,
    ADD COLUMN IF NOT EXISTS resuelto_por text,
    ADD COLUMN IF NOT EXISTS resuelto_en timestamptz;

CREATE TABLE IF NOT EXISTS aclaracion_docente (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cola        text NOT NULL UNIQUE REFERENCES cola_revision (id) ON DELETE CASCADE,
    clase       text NOT NULL REFERENCES clase (id),
    estudiante  text NOT NULL,
    sesion      text NOT NULL,
    docente     text NOT NULL,
    texto       text NOT NULL CHECK (btrim(texto) <> ''),
    creada_en   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS aclaracion_docente_por_hilo
    ON aclaracion_docente (estudiante, sesion, id);

COMMENT ON TABLE aclaracion_docente IS
    'Aclaración posterior de un docente a una respuesta marcada. La respuesta '
    'original permanece intacta en historial_turno y la aclaración se muestra '
    'como una voz separada, atribuida y auditable.';
