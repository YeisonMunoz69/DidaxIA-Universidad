CREATE TABLE IF NOT EXISTS persona (
    sujeto_google        text PRIMARY KEY CHECK (btrim(sujeto_google) <> ''),
    correo               text NOT NULL CHECK (position('@' in correo) > 1),
    nombre               text NOT NULL DEFAULT '',
    edad_declarada       integer CHECK (edad_declarada BETWEEN 0 AND 120),
    programa             text NOT NULL DEFAULT '',
    semestre             integer CHECK (semestre BETWEEN 1 AND 20),

    representante_limite timestamp with time zone,
    creada_en            timestamp with time zone NOT NULL DEFAULT now(),
    actualizada_en       timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS persona_por_correo ON persona (lower(correo));

CREATE TABLE IF NOT EXISTS consentimiento_finalidad (
    codigo        text PRIMARY KEY CHECK (codigo IN (
                      'autenticacion_y_seguridad',
                      'historial_conversacional',
                      'perfil_conductual',
                      'personalizacion_pedagogica',
                      'investigacion',
                      'visualizacion_docente')),
    registrada_en timestamp with time zone NOT NULL DEFAULT now()
);

INSERT INTO consentimiento_finalidad (codigo) VALUES
    ('autenticacion_y_seguridad'),
    ('historial_conversacional'),
    ('perfil_conductual'),
    ('personalizacion_pedagogica'),
    ('investigacion'),
    ('visualizacion_docente')
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS consentimiento_version (
    codigo           text PRIMARY KEY CHECK (btrim(codigo) <> ''),
    alcance          text NOT NULL
                         CHECK (alcance IN ('titular', 'asentimiento', 'representante')),
    huella_contenido text NOT NULL CHECK (huella_contenido ~ '^[0-9a-f]{64}$'),
    vigente_desde    timestamp with time zone NOT NULL,
    vigente_hasta    timestamp with time zone,
    registrada_en    timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT consentimiento_version_vigencia
        CHECK (vigente_hasta IS NULL OR vigente_hasta > vigente_desde),
    CONSTRAINT consentimiento_version_codigo_alcance UNIQUE (codigo, alcance)
);

CREATE INDEX IF NOT EXISTS consentimiento_version_por_alcance
    ON consentimiento_version (alcance, vigente_desde DESC, codigo DESC);

CREATE TABLE IF NOT EXISTS consentimiento_version_finalidad (
    version   text NOT NULL REFERENCES consentimiento_version (codigo) ON DELETE RESTRICT,
    finalidad text NOT NULL REFERENCES consentimiento_finalidad (codigo) ON DELETE RESTRICT,
    PRIMARY KEY (version, finalidad)
);

CREATE TABLE IF NOT EXISTS consentimiento_evento (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google  text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    version        text NOT NULL,
    alcance        text NOT NULL DEFAULT 'titular' CHECK (alcance = 'titular'),
    estado         text NOT NULL CHECK (estado IN ('otorgado', 'rechazado', 'revocado')),
    categoria_edad text NOT NULL CHECK (categoria_edad IN ('menor', 'adulto')),
    comprobante    text NOT NULL CHECK (comprobante ~ '^[0-9a-f]{64}$'),
    momento        timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT consentimiento_evento_version_titular
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS consentimiento_evento_por_sujeto
    ON consentimiento_evento (sujeto_google, momento DESC, id DESC);

CREATE TABLE IF NOT EXISTS asentimiento_evento (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    version       text NOT NULL,
    alcance       text NOT NULL DEFAULT 'asentimiento' CHECK (alcance = 'asentimiento'),
    estado        text NOT NULL CHECK (estado IN ('otorgado', 'rechazado', 'revocado')),
    comprobante   text NOT NULL CHECK (comprobante ~ '^[0-9a-f]{64}$'),
    momento       timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT asentimiento_evento_version_asentimiento
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS asentimiento_evento_por_sujeto
    ON asentimiento_evento (sujeto_google, momento DESC, id DESC);

CREATE TABLE IF NOT EXISTS representante_evidencia (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    intento       integer NOT NULL CHECK (intento > 0),
    version       text NOT NULL,
    alcance       text NOT NULL DEFAULT 'representante' CHECK (alcance = 'representante'),
    referencia    text NOT NULL
                      CHECK (btrim(referencia) <> '' AND referencia !~* '^https?://'),
    sha256        text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    tipo_mime     text NOT NULL CHECK (tipo_mime = 'application/pdf'),
    tamano_bytes  integer NOT NULL CHECK (tamano_bytes > 0 AND tamano_bytes <= 10485760),
    recibido_en   timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT representante_evidencia_intento_unico UNIQUE (sujeto_google, intento),
    CONSTRAINT representante_evidencia_version_representante
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS representante_evidencia_por_sujeto
    ON representante_evidencia (sujeto_google, version, intento DESC);

CREATE TABLE IF NOT EXISTS representante_revision (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evidencia    bigint NOT NULL REFERENCES representante_evidencia (id) ON DELETE RESTRICT,
    resultado    text NOT NULL CHECK (resultado IN ('aprobada', 'rechazada')),
    revisada_por text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    revisada_en  timestamp with time zone NOT NULL DEFAULT now(),
    motivo       text,
    CONSTRAINT representante_revision_motivo_al_rechazar
        CHECK (resultado <> 'rechazada' OR btrim(coalesce(motivo, '')) <> '')
);

CREATE INDEX IF NOT EXISTS representante_revision_por_evidencia
    ON representante_revision (evidencia, revisada_en DESC, id DESC);

CREATE TABLE IF NOT EXISTS rol_asignacion (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    rol           text NOT NULL CHECK (rol IN ('investigador_administrador')),
    otorgado_por  text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    otorgado_en   timestamp with time zone NOT NULL DEFAULT now(),
    revocado_por  text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    revocado_en   timestamp with time zone,
    CONSTRAINT rol_asignacion_revocacion_posterior
        CHECK (revocado_en IS NULL OR revocado_en >= otorgado_en),
    CONSTRAINT rol_asignacion_revocacion_auditada
        CHECK ((revocado_en IS NULL) = (revocado_por IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS rol_asignacion_vigente
    ON rol_asignacion (sujeto_google, rol)
    WHERE revocado_en IS NULL;

CREATE OR REPLACE FUNCTION didaxia_version_requerida(el_alcance text) RETURNS text
LANGUAGE sql STABLE AS $funcion$
SELECT mas_reciente.codigo
      FROM (
          SELECT codigo, vigente_hasta
            FROM consentimiento_version
           WHERE alcance = el_alcance
             AND vigente_desde <= now()
           ORDER BY vigente_desde DESC, codigo DESC
           LIMIT 1
      ) AS mas_reciente
     WHERE mas_reciente.vigente_hasta IS NULL
        OR now() < mas_reciente.vigente_hasta;
$funcion$;

CREATE OR REPLACE FUNCTION didaxia_version_del_acto() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    momento_del_acto timestamp with time zone;
    estado_del_acto  text;
    alcance_real     text;
    version_otorgada text;
    requerida        text;
BEGIN
    momento_del_acto := (to_jsonb(NEW) ->> TG_ARGV[0])::timestamp with time zone;
    estado_del_acto  := to_jsonb(NEW) ->> 'estado';

    IF momento_del_acto > now() THEN
        RAISE EXCEPTION 'un acto no se puede fechar en el futuro'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT alcance INTO alcance_real
      FROM consentimiento_version WHERE codigo = NEW.version;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la version referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF alcance_real <> NEW.alcance THEN
        RAISE EXCEPTION 'la version referenciada pertenece a otro alcance'
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF estado_del_acto = 'revocado' THEN

        EXECUTE format(
            'SELECT version FROM %I WHERE sujeto_google = $1 AND estado = ''otorgado'''
            || ' ORDER BY momento DESC, id DESC LIMIT 1', TG_TABLE_NAME)
          INTO version_otorgada USING NEW.sujeto_google;
        IF version_otorgada IS NULL OR version_otorgada <> NEW.version THEN
            RAISE EXCEPTION 'una revocacion solo retira la concesion efectivamente otorgada'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    requerida := didaxia_version_requerida(NEW.alcance);
    IF requerida IS NULL THEN
        RAISE EXCEPTION 'no hay version requerida vigente para este alcance'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.version <> requerida THEN
        RAISE EXCEPTION 'el acto tiene que usar la version requerida de su alcance'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_evento_version_del_acto
    BEFORE INSERT ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('momento');

CREATE OR REPLACE TRIGGER asentimiento_evento_version_del_acto
    BEFORE INSERT ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('momento');

CREATE OR REPLACE TRIGGER representante_evidencia_version_del_acto
    BEFORE INSERT ON representante_evidencia
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('recibido_en');

DROP TRIGGER IF EXISTS consentimiento_evento_version_vigente ON consentimiento_evento;

DROP TRIGGER IF EXISTS asentimiento_evento_version_vigente ON asentimiento_evento;

DROP TRIGGER IF EXISTS representante_evidencia_version_vigente ON representante_evidencia;

DROP FUNCTION IF EXISTS didaxia_version_vigente_en_el_acto();

CREATE OR REPLACE FUNCTION didaxia_derivar_categoria_edad() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    edad integer;
BEGIN
    SELECT p.edad_declarada INTO edad
      FROM persona p WHERE p.sujeto_google = NEW.sujeto_google;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la persona referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF edad IS NULL THEN
        RAISE EXCEPTION 'no se registra consentimiento sin edad declarada'
            USING ERRCODE = 'check_violation';
    END IF;

    NEW.categoria_edad := CASE WHEN edad < 18 THEN 'menor' ELSE 'adulto' END;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_evento_categoria_edad
    BEFORE INSERT ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_derivar_categoria_edad();

CREATE OR REPLACE FUNCTION didaxia_exigir_persona_menor() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    edad integer;
BEGIN
    SELECT p.edad_declarada INTO edad
      FROM persona p WHERE p.sujeto_google = NEW.sujeto_google;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la persona referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF edad IS NULL OR edad >= 18 THEN
        RAISE EXCEPTION 'el asentimiento solo corresponde a una persona menor de edad'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER asentimiento_evento_solo_menores
    BEFORE INSERT ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_exigir_persona_menor();

CREATE OR REPLACE FUNCTION didaxia_exigir_finalidades_obligatorias() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    sin_cubrir integer;
BEGIN
    SELECT count(*) INTO sin_cubrir
      FROM consentimiento_finalidad f
     WHERE NOT EXISTS (
         SELECT 1 FROM consentimiento_version_finalidad vf
          WHERE vf.version = NEW.codigo AND vf.finalidad = f.codigo);
    IF sin_cubrir > 0 THEN
        RAISE EXCEPTION 'una version publicada tiene que cubrir todas las finalidades obligatorias'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$funcion$;

CREATE CONSTRAINT TRIGGER consentimiento_version_finalidades_obligatorias
    AFTER INSERT ON consentimiento_version
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION didaxia_exigir_finalidades_obligatorias();

CREATE OR REPLACE FUNCTION didaxia_rechazar_modificacion() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
BEGIN
    RAISE EXCEPTION 'fila inmutable: esta tabla no admite UPDATE ni DELETE'
        USING ERRCODE = 'check_violation',
              HINT = 'la supresion procedente de EQ-022 es un camino aparte de la sesion 4';
    RETURN NULL;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_version_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER consentimiento_version_finalidad_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version_finalidad
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER consentimiento_evento_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER asentimiento_evento_inmutable
    BEFORE UPDATE OR DELETE ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER representante_evidencia_inmutable
    BEFORE UPDATE OR DELETE ON representante_evidencia
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER representante_revision_inmutable
    BEFORE UPDATE OR DELETE ON representante_revision
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
