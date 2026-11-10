\encoding UTF8

ALTER TABLE persona
    ADD COLUMN IF NOT EXISTS foto_perfil_referencia text;

DO $bloque$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'persona_foto_perfil_referencia_valida'
           AND conrelid = 'persona'::regclass
    ) THEN
        ALTER TABLE persona
            ADD CONSTRAINT persona_foto_perfil_referencia_valida
            CHECK (
                foto_perfil_referencia IS NULL
                OR foto_perfil_referencia ~ '^foto-[0-9a-f]{32}$'
            );
    END IF;
END
$bloque$;
