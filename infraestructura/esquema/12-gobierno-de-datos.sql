ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS consentimiento_evento bigint
        REFERENCES consentimiento_evento (id) ON DELETE RESTRICT;

ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS consentimiento_evento bigint
        REFERENCES consentimiento_evento (id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS registro_turno_por_consentimiento
    ON registro_turno (consentimiento_evento);

CREATE INDEX IF NOT EXISTS historial_turno_por_consentimiento
    ON historial_turno (consentimiento_evento);

CREATE TABLE IF NOT EXISTS solicitud_supresion (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google     text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    estado            text NOT NULL DEFAULT 'solicitada'
                          CHECK (estado IN ('solicitada', 'cancelada', 'ejecutada', 'rechazada')),
    solicitada_en     timestamp with time zone NOT NULL DEFAULT now(),

    solicitada_por    text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,

    reautenticada_en  timestamp with time zone NOT NULL,
    frase_confirmada  boolean NOT NULL DEFAULT false CHECK (frase_confirmada),

    cancelable_hasta  timestamp with time zone NOT NULL,
    resolver_antes_de timestamp with time zone NOT NULL,
    extension_hasta   timestamp with time zone,
    extension_motivo  text,
    cerrada_en        timestamp with time zone,
    CONSTRAINT solicitud_supresion_cancelacion_antes_del_plazo
        CHECK (cancelable_hasta <= resolver_antes_de),
    CONSTRAINT solicitud_supresion_extension_posterior
        CHECK (extension_hasta IS NULL OR extension_hasta > resolver_antes_de),

    CONSTRAINT solicitud_supresion_extension_motivada
        CHECK ((extension_hasta IS NULL) = (extension_motivo IS NULL)),
    CONSTRAINT solicitud_supresion_cierre_coherente
        CHECK ((estado = 'solicitada') = (cerrada_en IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS solicitud_supresion_abierta
    ON solicitud_supresion (sujeto_google)
    WHERE estado = 'solicitada';

CREATE INDEX IF NOT EXISTS solicitud_supresion_por_sujeto
    ON solicitud_supresion (sujeto_google, solicitada_en DESC, id DESC);

CREATE TABLE IF NOT EXISTS politica_retencion (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sustentacion_en   timestamp with time zone,
    meses_despues     integer NOT NULL DEFAULT 6 CHECK (meses_despues > 0),
    vigente_desde     timestamp with time zone NOT NULL DEFAULT now(),
    registrada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    nota              text
);

CREATE INDEX IF NOT EXISTS politica_retencion_vigente
    ON politica_retencion (vigente_desde DESC, id DESC);

CREATE TABLE IF NOT EXISTS auditoria_operacion (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operacion       text NOT NULL CHECK (btrim(operacion) <> ''),
    actor           text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    sujeto_afectado text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    momento         timestamp with time zone NOT NULL DEFAULT now(),
    detalle         jsonb NOT NULL DEFAULT '{}'::jsonb,

    exige_doble_aprobacion boolean NOT NULL DEFAULT false,
    aprobada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    CONSTRAINT auditoria_operacion_doble_aprobacion
        CHECK (NOT exige_doble_aprobacion OR aprobada_por IS NOT NULL),

    CONSTRAINT auditoria_operacion_aprobacion_de_otro
        CHECK (aprobada_por IS NULL OR aprobada_por <> actor)
);

CREATE INDEX IF NOT EXISTS auditoria_operacion_por_sujeto
    ON auditoria_operacion (sujeto_afectado, momento DESC, id DESC);

CREATE INDEX IF NOT EXISTS auditoria_operacion_por_actor
    ON auditoria_operacion (actor, momento DESC, id DESC);

CREATE TABLE IF NOT EXISTS propuesta_administrativa (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operacion      text NOT NULL CHECK (btrim(operacion) <> ''),
    payload        jsonb NOT NULL,
    huella         text NOT NULL CHECK (huella ~ '^[0-9a-f]{64}$'),
    propuesta_por  text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    propuesta_en   timestamp with time zone NOT NULL DEFAULT now(),
    estado         text NOT NULL DEFAULT 'pendiente'
                       CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    aprobada_por   text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    aprobada_en    timestamp with time zone,

    CONSTRAINT propuesta_aprobacion_de_otro
        CHECK (aprobada_por IS NULL OR aprobada_por <> propuesta_por),

    CONSTRAINT propuesta_aprobacion_completa
        CHECK ((aprobada_por IS NULL) = (aprobada_en IS NULL)),

    CONSTRAINT propuesta_estado_coherente
        CHECK ((estado = 'pendiente') = (aprobada_en IS NULL))
);

CREATE INDEX IF NOT EXISTS propuesta_administrativa_pendientes
    ON propuesta_administrativa (propuesta_en DESC, id DESC)
    WHERE estado = 'pendiente';

CREATE OR REPLACE TRIGGER auditoria_operacion_inmutable
    BEFORE UPDATE OR DELETE ON auditoria_operacion
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER politica_retencion_inmutable
    BEFORE UPDATE OR DELETE ON politica_retencion
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
