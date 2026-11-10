CREATE TABLE IF NOT EXISTS consentimiento_usuario (
    identificador_sujeto text PRIMARY KEY,
    correo               text,
    decision             text NOT NULL CHECK (decision IN ('otorgado', 'rechazado')),
    edad                 integer,
    momento              timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS consentimiento_usuario_correo
    ON consentimiento_usuario (correo);
