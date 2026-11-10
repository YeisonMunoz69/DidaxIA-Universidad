\encoding UTF8

BEGIN;

CREATE TABLE IF NOT EXISTS historial_bloque (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    orden       integer NOT NULL CHECK (orden >= 0),

    tipo        text NOT NULL CHECK (btrim(tipo) <> ''),
    contenido   text NOT NULL CHECK (btrim(contenido) <> ''),

    sello       text NOT NULL CHECK (sello IN ('verificado', 'generado')),

    alternativo text,

    UNIQUE (historial, orden),
    CONSTRAINT historial_bloque_alternativo_obligatorio
        CHECK (tipo NOT IN ('notacion', 'grafica') OR btrim(coalesce(alternativo, '')) <> '')
);

CREATE TABLE IF NOT EXISTS historial_cita (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    marca       text NOT NULL CHECK (btrim(marca) <> ''),
    expresion   text NOT NULL CHECK (btrim(expresion) <> ''),

    UNIQUE (historial, marca)
);

CREATE INDEX IF NOT EXISTS historial_bloque_por_mensaje ON historial_bloque (historial);

CREATE INDEX IF NOT EXISTS historial_cita_por_mensaje   ON historial_cita   (historial);

ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS nivel                   text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS procedencia_origen      text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS procedencia_referencia  text NOT NULL DEFAULT '';

COMMIT;
