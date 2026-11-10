-- ==============================================================================
-- 12-gobierno-de-datos.sql — Turnos ligados al consentimiento, solicitud de
-- supresión, retención y auditoría · EQ-022 · EQ-023 · Fase 3 · hito B3
-- ==============================================================================
--
-- Qué añade
-- -----------------------------------------------------------------------------
-- Lo **reversible y auditable** del gobierno de datos, y nada más:
--
--   1. cada turno nuevo referencia el evento de consentimiento vigente al
--      crearse, de modo que se pueda saber bajo qué autorización se recogió;
--   2. la solicitud de supresión de `EQ-022` con su ventana de cancelación, su
--      plazo operativo y su extensión excepcional;
--   3. la política de retención, representable y consultable;
--   4. un registro de auditoría de las operaciones administrativas.
--
-- ⚠️ **Lo que este archivo NO hace, y es el límite del hito**
-- -----------------------------------------------------------------------------
-- **No ejecuta ninguna eliminación ni anonimización irreversible.** El encargo
-- lo prohíbe con todas las letras y la razón está escrita en `ESTADO-ACTUAL.md`:
-- cambiar el sujeto técnico de una conversación sólo la **seudonimiza**, y su
-- texto puede seguir conteniendo nombres, correos u otros identificadores.
-- Declarar anónimo ese texto sería falso.
--
-- El cierre V-B decidirá qué textos se eliminan, qué datos pueden conservarse
-- seudonimizados hasta el límite de retención, qué métricas estructuradas pueden
-- anonimizarse de forma irreversible y qué evidencia de la operación se conserva.
-- Hasta entonces, aquí sólo se **registra la solicitud** y se **inventaría** el
-- alcance; no hay ni un DELETE ni un UPDATE que toque datos de nadie.
--
-- Por qué una migración 12 y no una corrección de la 11
-- -----------------------------------------------------------------------------
-- La 11 sigue en revisión y por eso se corrigió en su sitio. Ésta es un hito
-- distinto con un consumidor distinto —el gobierno de datos, no la identidad— y
-- fundirlas habría hecho que el rango que Sol revisa mezclara dos frentes en un
-- solo archivo. El catálogo admite versiones nuevas; lo que no admite es
-- reescribir una ya aplicada.
--
-- Aditivo y repetible
-- -----------------------------------------------------------------------------
-- `CREATE ... IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS` y `CREATE OR REPLACE`.
-- Ni un DROP, ni un DELETE, ni un UPDATE de datos. `registro_turno` e
-- `historial_turno` reciben una columna **anulable**: las filas que ya existan
-- se quedan con `NULL`, que significa «se recogió antes de que el sistema
-- exigiera el vínculo» y no se convierte en un consentimiento inventado.

-- ---------------------------------------------------------------------------
-- El vínculo turno → evento de consentimiento
-- ---------------------------------------------------------------------------
-- `ESTADO-ACTUAL.md` §Contrato humano, punto 6: *«cada turno referencia el
-- evento de consentimiento vigente al crearse»*. Sin esto, revocar dejaría el
-- historial sin forma de saber bajo qué autorización se recogió cada pieza, y la
-- decisión de V-B sobre qué se conserva no tendría con qué separar.
--
-- **Anulable a propósito.** Las filas anteriores a esta migración no tienen ese
-- vínculo y no se les puede inventar uno: `NULL` dice «no consta», que es la
-- verdad. `ON DELETE RESTRICT` porque un evento de consentimiento no se borra —
-- la migración 11 ya lo hace inmutable— y esta clave lo vuelve a decir.
ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS consentimiento_evento bigint
        REFERENCES consentimiento_evento (id) ON DELETE RESTRICT;

ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS consentimiento_evento bigint
        REFERENCES consentimiento_evento (id) ON DELETE RESTRICT;

COMMENT ON COLUMN registro_turno.consentimiento_evento IS
    'Bajo que evento de consentimiento se recogio este turno (EQ-016). NULL en '
    'las filas anteriores al hito B3: no consta, y no se inventa.';

COMMENT ON COLUMN historial_turno.consentimiento_evento IS
    'Bajo que evento de consentimiento se recogio este mensaje (EQ-016). NULL '
    'en las filas anteriores al hito B3: no consta, y no se inventa.';

CREATE INDEX IF NOT EXISTS registro_turno_por_consentimiento
    ON registro_turno (consentimiento_evento);

CREATE INDEX IF NOT EXISTS historial_turno_por_consentimiento
    ON historial_turno (consentimiento_evento);

-- ---------------------------------------------------------------------------
-- solicitud_supresion · el trámite de EQ-022
-- ---------------------------------------------------------------------------
-- `EQ-022` describe un trámite con pasos, plazos y actores, no un botón:
--
--   - reautenticación reciente con Google;
--   - diálogo explícito y frase de confirmación;
--   - aviso al correo institucional;
--   - **24 horas para cancelar** antes de ejecutarse;
--   - durante el trámite no se permite usar el tutor;
--   - plazo operativo de **15 días hábiles**, con extensión excepcional
--     informada de hasta 8 días hábiles adicionales.
--
-- Todo eso son datos, y aquí están. Lo que no está es la ejecución: `estado`
-- llega hasta `ejecutada` pero **nada en este árbol la escribe**, porque quién
-- decide qué se borra es el cierre V-B.
--
-- `frase_confirmada` es un booleano y no la frase: guardar el texto que la
-- persona escribió no aporta nada y sí crea un dato más que custodiar. La
-- comprobación la hace el backend contra la frase esperada (`EQ-024` exige
-- confirmación explícita) y aquí sólo queda constancia de que ocurrió.
CREATE TABLE IF NOT EXISTS solicitud_supresion (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google     text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    estado            text NOT NULL DEFAULT 'solicitada'
                          CHECK (estado IN ('solicitada', 'cancelada', 'ejecutada', 'rechazada')),
    solicitada_en     timestamp with time zone NOT NULL DEFAULT now(),
    -- Quién la pidió. Es el propio titular hoy; se guarda igual porque `EQ-023`
    -- audita cada operación y «se supone que fue él» no es una auditoría.
    solicitada_por    text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    -- `EQ-022` · reautenticación reciente. Se guarda CUÁNDO se reautenticó, no
    -- el token: el token es un secreto y su antigüedad es el dato que importa.
    reautenticada_en  timestamp with time zone NOT NULL,
    frase_confirmada  boolean NOT NULL DEFAULT false CHECK (frase_confirmada),
    -- Las tres fechas del trámite. Se calculan al solicitar y se conservan, en
    -- vez de derivarse al consultar: el plazo que rige es el que se comunicó.
    cancelable_hasta  timestamp with time zone NOT NULL,
    resolver_antes_de timestamp with time zone NOT NULL,
    extension_hasta   timestamp with time zone,
    extension_motivo  text,
    cerrada_en        timestamp with time zone,
    CONSTRAINT solicitud_supresion_cancelacion_antes_del_plazo
        CHECK (cancelable_hasta <= resolver_antes_de),
    CONSTRAINT solicitud_supresion_extension_posterior
        CHECK (extension_hasta IS NULL OR extension_hasta > resolver_antes_de),
    -- `EQ-022`: la extensión es **excepcional e informada**. Sin motivo no se
    -- registra: una prórroga sin explicación no es informada.
    CONSTRAINT solicitud_supresion_extension_motivada
        CHECK ((extension_hasta IS NULL) = (extension_motivo IS NULL)),
    CONSTRAINT solicitud_supresion_cierre_coherente
        CHECK ((estado = 'solicitada') = (cerrada_en IS NULL))
);

COMMENT ON TABLE solicitud_supresion IS
    'Tramite de supresion de EQ-022: reautenticacion, frase, ventana de 24h, '
    'plazo de 15 dias habiles y extension informada. NADA en este arbol ejecuta '
    'la eliminacion: esa decision es del cierre V-B.';

-- Una sola solicitud abierta por titular. Las cerradas se conservan: son la
-- evidencia de que el trámite ocurrió, y `EQ-022` habla de conservar deberes.
CREATE UNIQUE INDEX IF NOT EXISTS solicitud_supresion_abierta
    ON solicitud_supresion (sujeto_google)
    WHERE estado = 'solicitada';

CREATE INDEX IF NOT EXISTS solicitud_supresion_por_sujeto
    ON solicitud_supresion (sujeto_google, solicitada_en DESC, id DESC);

-- ---------------------------------------------------------------------------
-- politica_retencion · EQ-022, representable y consultable
-- ---------------------------------------------------------------------------
-- *«Los datos identificables o seudonimizados se conservan como máximo hasta
-- seis meses después de la sustentación.»* La fecha de sustentación no existe
-- todavía, así que la tabla nace **vacía** y quien pregunte recibe «sin fijar»
-- en vez de una fecha inventada.
--
-- Una fila por vigencia y no una fila que se edita: si el equipo mueve la fecha,
-- queda constancia de cuál se comunicó antes. `vigente_desde` la ordena.
CREATE TABLE IF NOT EXISTS politica_retencion (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sustentacion_en   timestamp with time zone,
    meses_despues     integer NOT NULL DEFAULT 6 CHECK (meses_despues > 0),
    vigente_desde     timestamp with time zone NOT NULL DEFAULT now(),
    registrada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    nota              text
);

COMMENT ON TABLE politica_retencion IS
    'Plazo de retencion de EQ-022. Nace vacia: la fecha de sustentacion no '
    'existe y una inventada seria peor que ninguna.';

CREATE INDEX IF NOT EXISTS politica_retencion_vigente
    ON politica_retencion (vigente_desde DESC, id DESC);

-- ---------------------------------------------------------------------------
-- auditoria_operacion · EQ-023
-- ---------------------------------------------------------------------------
-- *«Cada consulta de una conversación y cada cambio de permisos quedan
-- registrados.»* Esta tabla es ese registro para las operaciones
-- administrativas que el sistema ya sabe hacer.
--
-- ⚠️ **`detalle` no admite datos personales**, y no es una recomendación: quien
-- escribe aquí es `auditoria.py`, que sólo pasa identificadores y conteos. Un
-- registro de auditoría que copiara el texto de una conversación duplicaría
-- exactamente lo que la supresión tendría que borrar, y en una tabla que —por
-- ser auditoría— se conserva más tiempo.
--
-- `sujeto_afectado` admite NULL: hay operaciones que no son sobre una persona
-- —fijar la política de retención, por ejemplo—.
CREATE TABLE IF NOT EXISTS auditoria_operacion (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operacion       text NOT NULL CHECK (btrim(operacion) <> ''),
    actor           text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    sujeto_afectado text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    momento         timestamp with time zone NOT NULL DEFAULT now(),
    detalle         jsonb NOT NULL DEFAULT '{}'::jsonb,
    -- `EQ-023`: políticas, exportaciones masivas y eliminaciones excepcionales
    -- requieren aprobación de Yeison **y** Fabian. Se registra si esta operación
    -- la exigía y quién fue el segundo; sin él, la operación no procede.
    exige_doble_aprobacion boolean NOT NULL DEFAULT false,
    aprobada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    CONSTRAINT auditoria_operacion_doble_aprobacion
        CHECK (NOT exige_doble_aprobacion OR aprobada_por IS NOT NULL),
    -- Nadie se aprueba a sí mismo: dos aprobaciones de la misma persona son una.
    CONSTRAINT auditoria_operacion_aprobacion_de_otro
        CHECK (aprobada_por IS NULL OR aprobada_por <> actor)
);

COMMENT ON TABLE auditoria_operacion IS
    'Registro de operaciones administrativas (EQ-023). `detalle` lleva '
    'identificadores y conteos, nunca texto de conversaciones ni datos '
    'personales: la auditoria se conserva mas tiempo que lo que audita.';

CREATE INDEX IF NOT EXISTS auditoria_operacion_por_sujeto
    ON auditoria_operacion (sujeto_afectado, momento DESC, id DESC);

CREATE INDEX IF NOT EXISTS auditoria_operacion_por_actor
    ON auditoria_operacion (actor, momento DESC, id DESC);

-- ---------------------------------------------------------------------------
-- propuesta_administrativa · la doble aprobación de EQ-023, de verdad
-- ---------------------------------------------------------------------------
-- *«Nuevas políticas, exportaciones masivas y eliminaciones excepcionales
-- requieren aprobación de ambos.»*
--
-- ⚠️ **Por qué hizo falta una tabla, y no bastaba `auditoria_operacion`.**
-- La primera versión de este hito guardaba `aprobada_por` en el registro de
-- auditoría y creía haber implementado la doble aprobación. No lo estaba: el
-- primer administrador escribía en el cuerpo de SU petición el identificador
-- del segundo, y el sistema lo aceptaba como prueba de que aquel había
-- aprobado. Una aprobación que la firma el otro no es una aprobación; es un
-- campo de texto. La auditoría V-B lo devolvió como cuarto invariante:
--
--     «Dos aprobaciones significan dos actos autenticados.»
--
-- Dos actos autenticados necesitan algo que persista **entre** los dos, y eso
-- es esta tabla: la primera petición deja una propuesta pendiente y la segunda,
-- de otra sesión y otro administrador, la aprueba.
--
-- `payload` es el contenido propuesto y `huella` su SHA-256 canónico. Los dos,
-- y no sólo el primero: la huella es lo que permite afirmar que **lo aprobado
-- es exactamente lo propuesto** sin tener que comparar JSON campo a campo, y se
-- recomputa al aprobar. Si alguien alterase la fila entre las dos peticiones,
-- la comparación fallaría y la aprobación no procedería.
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
    -- Nadie aprueba lo suyo. Es la misma regla que `auditoria_operacion` ya
    -- exige, repetida aquí para que no dependa de pasar por aquella tabla.
    CONSTRAINT propuesta_aprobacion_de_otro
        CHECK (aprobada_por IS NULL OR aprobada_por <> propuesta_por),
    -- Autor y fecha de la aprobación van juntos, o no van.
    CONSTRAINT propuesta_aprobacion_completa
        CHECK ((aprobada_por IS NULL) = (aprobada_en IS NULL)),
    -- Y una propuesta pendiente no puede tener aprobación, ni una aprobada
    -- carecer de ella: el estado y sus columnas dicen lo mismo o la fila no entra.
    CONSTRAINT propuesta_estado_coherente
        CHECK ((estado = 'pendiente') = (aprobada_en IS NULL))
);

COMMENT ON TABLE propuesta_administrativa IS
    'Doble aprobacion de EQ-023: la primera peticion autenticada deja una '
    'propuesta pendiente con su payload canonico y su huella; un segundo '
    'administrador distinto la aprueba en OTRA peticion autenticada. El primero '
    'no puede afirmar que el segundo aprobo.';

COMMENT ON COLUMN propuesta_administrativa.huella IS
    'SHA-256 del payload canonico. Se recomputa al aprobar para garantizar que '
    'el contenido aprobado es exactamente el propuesto.';

CREATE INDEX IF NOT EXISTS propuesta_administrativa_pendientes
    ON propuesta_administrativa (propuesta_en DESC, id DESC)
    WHERE estado = 'pendiente';

-- ---------------------------------------------------------------------------
-- Inmutabilidad de la auditoría
-- ---------------------------------------------------------------------------
-- Un registro de auditoría que se puede editar no audita nada. Se reutiliza el
-- disparador de la migración 11 —una sola definición— y se aplica también a los
-- eventos de supresión ya cerrados.
--
-- `solicitud_supresion` NO es inmutable: su estado cambia —se cancela, se
-- resuelve, se extiende— y ése es su ciclo de vida. Lo que la protege es el
-- índice único parcial, que impide dos trámites abiertos a la vez, y el CHECK
-- que exige coherencia entre estado y cierre.
CREATE OR REPLACE TRIGGER auditoria_operacion_inmutable
    BEFORE UPDATE OR DELETE ON auditoria_operacion
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER politica_retencion_inmutable
    BEFORE UPDATE OR DELETE ON politica_retencion
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
