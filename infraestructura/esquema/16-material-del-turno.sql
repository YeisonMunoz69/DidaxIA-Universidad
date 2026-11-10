\encoding UTF8

BEGIN;

CREATE TABLE IF NOT EXISTS historial_material (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    orden       integer NOT NULL CHECK (orden >= 0),

    fragmento   text NOT NULL CHECK (fragmento ~ '^F-[0-9]{3}$'),

    obra        text NOT NULL CHECK (obra ~ '^[A-Z]{3}$'),

    relacion    text NOT NULL DEFAULT 'recuperado'
                CHECK (relacion IN (
                    'recuperado',
                    'soporte_del_turno',
                    'cita_literal',
                    'respaldo_de_afirmacion'
                )),

    similitud   real CHECK (similitud IS NULL OR (similitud >= 0 AND similitud <= 1)),

    UNIQUE (historial, orden),

    UNIQUE (historial, fragmento)
);

CREATE INDEX IF NOT EXISTS historial_material_por_mensaje
    ON historial_material (historial);

CREATE INDEX IF NOT EXISTS historial_material_por_obra
    ON historial_material (obra);

COMMIT;
