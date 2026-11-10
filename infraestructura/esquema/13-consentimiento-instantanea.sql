\encoding UTF8

CREATE TABLE IF NOT EXISTS consentimiento_version_texto (
    version       text PRIMARY KEY
                      REFERENCES consentimiento_version (codigo) ON DELETE RESTRICT,
    cuerpo        text NOT NULL,
    medio         text NOT NULL DEFAULT 'text/markdown'
                      CHECK (medio IN ('text/markdown')),
    registrada_en timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT consentimiento_version_texto_no_vacio
        CHECK (btrim(cuerpo) <> ''),
    CONSTRAINT consentimiento_version_texto_salto_final
        CHECK (cuerpo LIKE E'%\n' AND cuerpo NOT LIKE E'%\n\n'),
    CONSTRAINT consentimiento_version_texto_sin_retorno
        CHECK (position(E'\r' in cuerpo) = 0)
);

CREATE OR REPLACE TRIGGER consentimiento_version_texto_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version_texto
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
