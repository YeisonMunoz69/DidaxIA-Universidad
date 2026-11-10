CREATE TABLE IF NOT EXISTS configuracion_sondeos (
    unica             boolean PRIMARY KEY DEFAULT true CHECK (unica),
    l01_aula          boolean NOT NULL DEFAULT true,
    n08_digital       boolean NOT NULL DEFAULT false,
    n14_digital       boolean NOT NULL DEFAULT false,
    n05_digital       boolean NOT NULL DEFAULT false,
    umbral_intentos   smallint NOT NULL DEFAULT 2 CHECK (umbral_intentos IN (1, 2)),
    actualizado_en    timestamptz NOT NULL DEFAULT now(),
    actualizado_por   text REFERENCES persona(sujeto_google)
);

INSERT INTO configuracion_sondeos (unica) VALUES (true)
ON CONFLICT (unica) DO NOTHING;
