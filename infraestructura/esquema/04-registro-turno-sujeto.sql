\encoding UTF8

BEGIN;

DO $$
DECLARE
    filas_purgadas bigint;
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name   = 'registro_turno'
           AND column_name  = 'identificador_sujeto'
    ) THEN
        RAISE NOTICE
            '04-registro-turno-sujeto · la columna ya existe: NO se purga nada.';
    ELSE
        SELECT count(*) INTO filas_purgadas FROM registro_turno;
        DELETE FROM registro_turno;
        RAISE NOTICE
            '04-registro-turno-sujeto · purgadas % filas previas a la migracion (D-29). Sus archivos JSON quedan huerfanos: retirarlos aparte.',
            filas_purgadas;
    END IF;
END
$$;

ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS identificador_sujeto text NOT NULL
        CHECK (btrim(identificador_sujeto) <> '');

CREATE INDEX IF NOT EXISTS registro_turno_por_sujeto
    ON registro_turno (identificador_sujeto);

COMMIT;
