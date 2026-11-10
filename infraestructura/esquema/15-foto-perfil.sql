\encoding UTF8
-- 15-foto-perfil.sql · referencia opaca a una fotografía privada
-- Los bytes no entran a PostgreSQL ni a la imagen Docker. La referencia nunca
-- es una ruta y su forma cerrada impide convertirla en traversal de archivos.

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

COMMENT ON COLUMN persona.foto_perfil_referencia IS
    'Referencia opaca a un WebP privado. Los bytes viven en la custodia de fotos, nunca en PostgreSQL.';
