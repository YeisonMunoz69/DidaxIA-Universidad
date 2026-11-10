-- Extensiones que ADR-004 y ADR-010 necesitan
-- ===========================================
--
-- Se activan al crear la base por primera vez. Las tres están en la imagen; lo
-- que falta es declararlas en ESTA base, que es lo que hace CREATE EXTENSION.
--
-- ⚠️ Este archivo se ejecuta UNA sola vez, cuando el volumen de datos se crea.
-- Si ya existe, el contenedor lo ignora sin avisar. Para volver a ejecutarlo:
--     docker compose down -v   (borra los datos, no solo el contenedor)
--
-- Cada una está aquí por un mecanismo concreto de `ADR-004` §7.1, no por si
-- acaso. Si alguna sobra, sobra el mecanismo, y eso sería cambiar la decisión.

-- `ADR-010` · el índice vectorial. Es la única que no viene de serie en una
-- distribución de PostgreSQL, y la razón de usar una imagen que ya la trae.
CREATE EXTENSION IF NOT EXISTS vector;

-- `ADR-004` C1 · versionado sin sobrescritura.
--
-- La condición dice que «la base rechaza FÍSICAMENTE dos versiones vigentes del
-- mismo registro. No depende de que nadie escriba una actualización». Eso es una
-- restricción de exclusión sobre un rango temporal más el identificador del
-- registro, y una exclusión que mezcla `=` sobre un entero con `&&` sobre un
-- rango necesita esta extensión: sin ella el índice GiST no sabe comparar el
-- entero y la restricción no se puede crear.
--
-- Es el mecanismo por el que se prefirió hacerlo en el motor y no en la
-- aplicación, así que sin esto la decisión pierde su argumento.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- `ADR-004` C4 · cifrado de columna para lo que `RD-15` clasifica como
-- identificador directo o dato inferido sensible. El cifrado del volumen es
-- cosa del sistema anfitrión; esto es la otra mitad.
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- Comprobación inmediata, que es la diferencia entre declarar y verificar
-- ----------------------------------------------------------------------
-- Si algo no quedó activo, el arranque falla aquí y no tres semanas después al
-- crear una tabla. Un paso que falla en silencio necesita su comprobación
-- inmediata: es la lección que la bitácora del 2026-08-06 dejó escrita cuando
-- un entorno virtual no se activó y nadie lo notó.
DO $$
DECLARE
    faltan text;
BEGIN
    SELECT string_agg(e, ', ')
      INTO faltan
      FROM unnest(ARRAY['vector', 'btree_gist', 'pgcrypto']) AS e
     WHERE e NOT IN (SELECT extname FROM pg_extension);

    IF faltan IS NOT NULL THEN
        RAISE EXCEPTION 'no quedaron activas las extensiones: %', faltan;
    END IF;

    RAISE NOTICE 'extensiones activas: vector, btree_gist, pgcrypto';
END
$$;
