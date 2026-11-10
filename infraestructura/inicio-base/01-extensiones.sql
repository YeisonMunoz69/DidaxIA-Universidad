CREATE EXTENSION IF NOT EXISTS vector;

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
