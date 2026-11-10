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
