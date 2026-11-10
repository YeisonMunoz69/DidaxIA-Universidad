\encoding UTF8

ALTER TABLE persona
    ADD COLUMN IF NOT EXISTS es_cuenta_prueba boolean NOT NULL DEFAULT false;
