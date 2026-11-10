\encoding UTF8

BEGIN;

CREATE TABLE registro_turno (

    turno                text PRIMARY KEY,
    identificador_sesion text NOT NULL CHECK (btrim(identificador_sesion) <> ''),
    ruta_archivo         text NOT NULL CHECK (btrim(ruta_archivo) <> ''),
    nivel_divulgacion    integer NOT NULL,
    latencia_total_ms    real NOT NULL CHECK (latencia_total_ms >= 0),
    creado_en            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX registro_turno_por_sesion ON registro_turno (identificador_sesion);

COMMIT;
