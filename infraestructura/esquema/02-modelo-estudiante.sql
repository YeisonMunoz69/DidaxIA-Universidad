\encoding UTF8

BEGIN;

CREATE TABLE perfil_afectivo (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    subcomponente      text NOT NULL CHECK (btrim(subcomponente) <> ''),
    alcance            text NOT NULL CHECK (alcance IN ('estado', 'rasgo')),

    turno              text NOT NULL,
    señal              text NOT NULL,
    regla_aplicada     text NOT NULL CHECK (btrim(regla_aplicada) <> ''),
    valor_previo       real NOT NULL CHECK (valor_previo BETWEEN 0 AND 1),
    valor_nuevo        real NOT NULL CHECK (valor_nuevo BETWEEN 0 AND 1),
    lambda_aplicado    real NOT NULL CHECK (lambda_aplicado BETWEEN 0 AND 1),
    certeza            real NOT NULL CHECK (certeza BETWEEN 0 AND 1),

    vigencia           tstzrange NOT NULL DEFAULT tstzrange(now(), NULL),

    creado_en          timestamptz NOT NULL DEFAULT now(),

    EXCLUDE USING gist (
        identificador_sujeto WITH =,
        subcomponente        WITH =,
        alcance               WITH =,
        vigencia              WITH &&
    )
);

CREATE INDEX perfil_afectivo_vigente ON perfil_afectivo (identificador_sujeto, subcomponente, alcance)
    WHERE upper(vigencia) IS NULL;

CREATE TABLE perfil_conceptual (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    elemento           text NOT NULL CHECK (btrim(elemento) <> ''),

    turno              text NOT NULL,
    estado_previo      text NOT NULL CHECK (estado_previo IN ('no_detectada', 'activa', 'remediada', 'recurrente')),
    estado_nuevo       text NOT NULL CHECK (estado_nuevo IN ('no_detectada', 'activa', 'remediada', 'recurrente')),
    evento_diagnostico text NOT NULL DEFAULT '',

    creado_en          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX perfil_conceptual_por_sujeto ON perfil_conceptual (identificador_sujeto, elemento, creado_en DESC);

CREATE TABLE perfil_estrategico (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    turno              text NOT NULL,
    tipo_evento        text NOT NULL CHECK (btrim(tipo_evento) <> ''),
    ventana            integer NOT NULL CHECK (ventana > 0),
    contador           integer NOT NULL CHECK (contador >= 0),
    ciclo_negativo     boolean NOT NULL DEFAULT false,

    creado_en          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX perfil_estrategico_por_sujeto ON perfil_estrategico (identificador_sujeto, creado_en DESC);

COMMIT;
