-- Consumo de IA y estimaciones financieras institucionales · Fase 8
-- Incremental e idempotente. Los hechos no contienen prompts, respuestas,
-- llaves, correos, sujetos ni identificadores de clases.

BEGIN;

CREATE TABLE IF NOT EXISTS consumo_ia_llamada (
    llamada                 uuid PRIMARY KEY,
    instante_utc            timestamp with time zone NOT NULL,
    proveedor               text NOT NULL CHECK (btrim(proveedor) <> ''),
    modelo_solicitado       text NOT NULL CHECK (btrim(modelo_solicitado) <> ''),
    modelo_respondido       text,
    respuesta_proveedor     text,
    es_local                boolean NOT NULL DEFAULT false,
    estado                  text NOT NULL
                                CHECK (estado IN ('completada', 'fallida', 'sin_medicion')),
    reintento               integer NOT NULL DEFAULT 0 CHECK (reintento >= 0),
    entrada_cache_hit       bigint CHECK (entrada_cache_hit >= 0),
    entrada_cache_miss      bigint CHECK (entrada_cache_miss >= 0),
    entrada_total           bigint CHECK (entrada_total >= 0),
    salida                  bigint CHECK (salida >= 0),
    total                   bigint CHECK (total >= 0),
    registrado_en           timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT consumo_ia_medicion_coherente CHECK (
        estado <> 'completada' OR (entrada_total IS NOT NULL AND salida IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS consumo_ia_respuesta_unica
    ON consumo_ia_llamada (proveedor, respuesta_proveedor)
    WHERE respuesta_proveedor IS NOT NULL AND btrim(respuesta_proveedor) <> '';

CREATE INDEX IF NOT EXISTS consumo_ia_por_periodo
    ON consumo_ia_llamada (instante_utc, proveedor, modelo_respondido);

CREATE TABLE IF NOT EXISTS tarifa_ia (
    id                                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proveedor                           text NOT NULL,
    modelo                              text NOT NULL,
    franja                              text NOT NULL CHECK (franja IN ('pico', 'fuera_pico')),
    vigente_desde                       timestamp with time zone NOT NULL,
    vigente_hasta                       timestamp with time zone,
    entrada_cache_hit_usd_millon        numeric(20, 9) NOT NULL CHECK (entrada_cache_hit_usd_millon >= 0),
    entrada_cache_miss_usd_millon       numeric(20, 9) NOT NULL CHECK (entrada_cache_miss_usd_millon >= 0),
    salida_usd_millon                   numeric(20, 9) NOT NULL CHECK (salida_usd_millon >= 0),
    fuente                              text NOT NULL CHECK (btrim(fuente) <> ''),
    consultada_en                       timestamp with time zone NOT NULL,
    CONSTRAINT tarifa_ia_vigencia CHECK (vigente_hasta IS NULL OR vigente_hasta > vigente_desde),
    CONSTRAINT tarifa_ia_version_unica UNIQUE (proveedor, modelo, franja, vigente_desde)
);

CREATE INDEX IF NOT EXISTS tarifa_ia_busqueda
    ON tarifa_ia (proveedor, modelo, franja, vigente_desde DESC);

CREATE TABLE IF NOT EXISTS trm_oficial_cache (
    fecha               date PRIMARY KEY,
    pesos_por_usd       numeric(18, 6) NOT NULL CHECK (pesos_por_usd > 0),
    fuente              text NOT NULL CHECK (btrim(fuente) <> ''),
    consultada_en       timestamp with time zone NOT NULL,
    es_ultima_disponible boolean NOT NULL DEFAULT false
);

-- Tarifas verificadas el 2026-09-13 10:25 UTC. La vigencia empieza en el instante de
-- verificación: no se inventa una tarifa histórica anterior.
INSERT INTO tarifa_ia (
    proveedor, modelo, franja, vigente_desde, vigente_hasta,
    entrada_cache_hit_usd_millon, entrada_cache_miss_usd_millon,
    salida_usd_millon, fuente, consultada_en
) VALUES
    ('deepseek', 'DeepSeek-V4.1-Flash', 'fuera_pico', '2026-09-13 10:25:00+00', NULL, 0.003, 0.15, 0.60, 'https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8', '2026-09-13 10:25:00+00'),
    ('deepseek', 'DeepSeek-V4.1-Flash', 'pico',        '2026-09-13 10:25:00+00', NULL, 0.006, 0.30, 1.20, 'https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8', '2026-09-13 10:25:00+00'),
    ('deepseek', 'DeepSeek-V4-Pro-0813', 'fuera_pico','2026-09-13 10:25:00+00', NULL, 0.022, 0.66, 1.98, 'https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8', '2026-09-13 10:25:00+00'),
    ('deepseek', 'DeepSeek-V4-Pro-0813', 'pico',       '2026-09-13 10:25:00+00', NULL, 0.044, 1.32, 3.96, 'https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8', '2026-09-13 10:25:00+00')
ON CONFLICT (proveedor, modelo, franja, vigente_desde) DO NOTHING;

CREATE OR REPLACE TRIGGER consumo_ia_llamada_inmutable
    BEFORE UPDATE OR DELETE ON consumo_ia_llamada
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER tarifa_ia_inmutable
    BEFORE UPDATE OR DELETE ON tarifa_ia
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

COMMENT ON TABLE consumo_ia_llamada IS
    'Hechos append-only e idempotentes de consumo de proveedor; nunca almacena contenido ni identidad personal.';
COMMENT ON TABLE tarifa_ia IS
    'Tarifas versionadas para estimaciones reproducibles; no representan cargos reales de facturación.';
COMMENT ON TABLE trm_oficial_cache IS
    'Cache servidor de TRM oficial por fecha, con fuente y momento de consulta.';

COMMIT;
