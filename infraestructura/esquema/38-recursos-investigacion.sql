CREATE TABLE IF NOT EXISTS recurso_investigacion (
    id text PRIMARY KEY,
    autor text NOT NULL,
    tipo text NOT NULL CHECK (tipo IN ('encuesta','diapositivas')),
    titulo text NOT NULL,
    descripcion text NOT NULL DEFAULT '',
    contenido jsonb NOT NULL,
    estado text NOT NULL DEFAULT 'borrador'
        CHECK (estado IN ('borrador','publicado','cerrado','archivado')),
    revision integer NOT NULL DEFAULT 1,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recurso_publicacion (
    id text PRIMARY KEY,
    recurso text NOT NULL REFERENCES recurso_investigacion(id) ON DELETE CASCADE,
    clase text NOT NULL REFERENCES clase(id) ON DELETE CASCADE,
    publicada_en timestamptz NOT NULL DEFAULT now(),
    UNIQUE (recurso, clase)
);

CREATE TABLE IF NOT EXISTS recurso_respuesta (
    publicacion text NOT NULL REFERENCES recurso_publicacion(id) ON DELETE CASCADE,
    sujeto_google text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    respuestas jsonb NOT NULL,
    enviada_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publicacion, sujeto_google)
);

CREATE TABLE IF NOT EXISTS recurso_visita (
    publicacion text NOT NULL REFERENCES recurso_publicacion(id) ON DELETE CASCADE,
    sujeto_google text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    primera_en timestamptz NOT NULL DEFAULT now(),
    ultima_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publicacion, sujeto_google)
);

CREATE INDEX IF NOT EXISTS recurso_publicacion_clase ON recurso_publicacion(clase);

CREATE INDEX IF NOT EXISTS recurso_respuesta_titular ON recurso_respuesta(sujeto_google);

CREATE INDEX IF NOT EXISTS recurso_visita_titular ON recurso_visita(sujeto_google);
