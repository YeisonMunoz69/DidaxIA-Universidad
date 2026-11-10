\encoding UTF8

CREATE OR REPLACE FUNCTION didaxia_version_requerida(el_alcance text) RETURNS text
LANGUAGE sql STABLE AS $funcion$
SELECT mas_reciente.codigo
      FROM (

          SELECT codigo, vigente_hasta, huella_contenido
            FROM consentimiento_version
           WHERE alcance = el_alcance
             AND vigente_desde <= now()
           ORDER BY vigente_desde DESC, codigo DESC
           LIMIT 1
      ) AS mas_reciente

      JOIN consentimiento_version_texto AS texto
        ON texto.version = mas_reciente.codigo
     WHERE (mas_reciente.vigente_hasta IS NULL OR now() < mas_reciente.vigente_hasta)
       AND encode(sha256(convert_to(texto.cuerpo, 'UTF8')), 'hex')
           = mas_reciente.huella_contenido;
$funcion$;

CREATE OR REPLACE FUNCTION didaxia_version_decidible(el_codigo text) RETURNS boolean
LANGUAGE sql STABLE AS $funcion$
SELECT EXISTS (
        SELECT 1
          FROM consentimiento_version AS version
          JOIN consentimiento_version_texto AS texto
            ON texto.version = version.codigo
         WHERE version.codigo = el_codigo
           AND encode(sha256(convert_to(texto.cuerpo, 'UTF8')), 'hex')
               = version.huella_contenido
    );
$funcion$;
