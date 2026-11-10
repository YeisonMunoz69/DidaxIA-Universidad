\encoding UTF8
-- Rectificaciones sucesivas: sustitución explícita y cierre por categoría.

BEGIN;

ALTER TABLE rectificacion_edad_transicion
    DROP CONSTRAINT IF EXISTS rectificacion_edad_transicion_estado_check;
ALTER TABLE rectificacion_edad_transicion
    ADD CONSTRAINT rectificacion_edad_transicion_estado_check CHECK (estado IN (
        'registrada', 'aplicada', 'reconsentimiento_pendiente',
        'reconsentida', 'sustituida'
    ));

CREATE OR REPLACE FUNCTION didaxia_cerrar_reconsentimiento_por_edad()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    pendiente record;
BEGIN
    IF NEW.estado <> 'otorgado' THEN
        RETURN NEW;
    END IF;

    FOR pendiente IN
        SELECT r.id
          FROM rectificacion_edad r
         WHERE r.sujeto_google = NEW.sujeto_google
           AND r.reconsentimiento_necesario
           AND (CASE WHEN r.valor_nuevo < 18 THEN 'menor' ELSE 'adulto' END)
               = NEW.categoria_edad
           AND EXISTS (
               SELECT 1 FROM rectificacion_edad_transicion t
                WHERE t.rectificacion = r.id
                  AND t.estado = 'reconsentimiento_pendiente'
           )
           AND NOT EXISTS (
               SELECT 1 FROM rectificacion_edad_transicion t
                WHERE t.rectificacion = r.id
                  AND t.estado IN ('reconsentida', 'sustituida')
           )
         ORDER BY r.registrada_en, r.id
    LOOP
        INSERT INTO rectificacion_edad_transicion
            (rectificacion, estado, actor, motivo)
        VALUES (
            pendiente.id,
            'reconsentida',
            NEW.sujeto_google,
            'nuevo consentimiento otorgado para la categoría vigente'
        )
        ON CONFLICT (rectificacion, estado) DO NOTHING;
    END LOOP;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION didaxia_cerrar_reconsentimiento_por_edad() IS
    'Cierra todos los trámites pendientes no sustituidos cuya categoría objetivo coincide con el nuevo consentimiento.';

COMMIT;
