CREATE TABLE IF NOT EXISTS clase (
    id         text PRIMARY KEY,
    nombre     text NOT NULL,
    creador    text NOT NULL,
    codigo     text NOT NULL UNIQUE,
    creada_en  timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS clase_creador
    ON clase (creador);

CREATE TABLE IF NOT EXISTS clase_matricula (
    clase          text NOT NULL REFERENCES clase (id) ON DELETE CASCADE,
    identificador  text NOT NULL,
    desde          timestamp with time zone NOT NULL DEFAULT now(),
    PRIMARY KEY (clase, identificador)
);

CREATE INDEX IF NOT EXISTS clase_matricula_identificador
    ON clase_matricula (identificador);
