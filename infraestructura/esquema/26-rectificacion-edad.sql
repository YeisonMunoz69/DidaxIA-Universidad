\encoding UTF8
-- Rectificación histórica de edad y separación tutoría/investigación · Fase 8

BEGIN;

ALTER TABLE historial_turno
    DROP CONSTRAINT IF EXISTS historial_turno_contexto_de_uso_check;
ALTER TABLE historial_turno
    ADD CONSTRAINT historial_turno_contexto_de_uso_check CHECK (
        contexto_de_uso IN (
            'aprendizaje_estudiante', 'consulta_profesional',
            'tutoria_academica_sin_investigacion'
        )
    );

ALTER TABLE registro_turno
    DROP CONSTRAINT IF EXISTS registro_turno_contexto_de_uso_check;
ALTER TABLE registro_turno
    ADD CONSTRAINT registro_turno_contexto_de_uso_check CHECK (
        contexto_de_uso IN (
            'aprendizaje_estudiante', 'consulta_profesional',
            'tutoria_academica_sin_investigacion'
        )
    );

CREATE TABLE IF NOT EXISTS rectificacion_edad (
    id                       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google            text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    valor_anterior           integer NOT NULL CHECK (valor_anterior BETWEEN 0 AND 120),
    valor_nuevo              integer NOT NULL CHECK (valor_nuevo BETWEEN 0 AND 120),
    actor                    text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    registrada_en            timestamp with time zone NOT NULL DEFAULT now(),
    motivo                   text NOT NULL CHECK (length(btrim(motivo)) BETWEEN 8 AND 500),
    efecto_consentimiento    text NOT NULL CHECK (efecto_consentimiento IN (
                                  'sin_cambio_de_categoria',
                                  'reconsentimiento_por_cambio_de_categoria')),
    efecto_asentimiento      text NOT NULL CHECK (efecto_asentimiento IN (
                                  'sin_cambio', 'pasa_a_requerir', 'deja_de_requerir')),
    reconsentimiento_necesario boolean NOT NULL,
    CONSTRAINT rectificacion_edad_cambia_valor CHECK (valor_anterior <> valor_nuevo)
);

CREATE TABLE IF NOT EXISTS rectificacion_edad_transicion (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rectificacion    bigint NOT NULL REFERENCES rectificacion_edad (id) ON DELETE RESTRICT,
    estado           text NOT NULL CHECK (estado IN (
                         'registrada', 'aplicada', 'reconsentimiento_pendiente',
                         'reconsentida')),
    actor            text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    momento          timestamp with time zone NOT NULL DEFAULT now(),
    motivo           text NOT NULL DEFAULT '' CHECK (length(motivo) <= 500),
    UNIQUE (rectificacion, estado)
);

CREATE INDEX IF NOT EXISTS rectificacion_edad_por_sujeto
    ON rectificacion_edad (sujeto_google, registrada_en DESC, id DESC);
CREATE INDEX IF NOT EXISTS rectificacion_edad_transicion_por_tramite
    ON rectificacion_edad_transicion (rectificacion, momento, id);

CREATE OR REPLACE TRIGGER rectificacion_edad_inmutable
    BEFORE UPDATE OR DELETE ON rectificacion_edad
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
CREATE OR REPLACE TRIGGER rectificacion_edad_transicion_inmutable
    BEFORE UPDATE OR DELETE ON rectificacion_edad_transicion
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE FUNCTION didaxia_cerrar_reconsentimiento_por_edad()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    pendiente bigint;
BEGIN
    IF NEW.estado <> 'otorgado' THEN
        RETURN NEW;
    END IF;
    SELECT r.id INTO pendiente
      FROM rectificacion_edad r
     WHERE r.sujeto_google = NEW.sujeto_google
       AND r.reconsentimiento_necesario
       AND NOT EXISTS (
           SELECT 1 FROM rectificacion_edad_transicion t
            WHERE t.rectificacion = r.id AND t.estado = 'reconsentida'
       )
     ORDER BY r.registrada_en DESC, r.id DESC
     LIMIT 1;
    IF pendiente IS NOT NULL THEN
        INSERT INTO rectificacion_edad_transicion
            (rectificacion, estado, actor, motivo)
        VALUES (pendiente, 'reconsentida', NEW.sujeto_google,
                'nuevo consentimiento otorgado para la categoría vigente')
        ON CONFLICT (rectificacion, estado) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS consentimiento_cierra_rectificacion_edad
    ON consentimiento_evento;
CREATE TRIGGER consentimiento_cierra_rectificacion_edad
    AFTER INSERT ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_cerrar_reconsentimiento_por_edad();

COMMENT ON TABLE rectificacion_edad IS
    'Actos inmutables de rectificación de edad; nunca sobrescriben consentimientos o asentimientos anteriores.';
COMMENT ON TABLE rectificacion_edad_transicion IS
    'Historia append-only del trámite de rectificación y su reconsentimiento.';

COMMIT;
