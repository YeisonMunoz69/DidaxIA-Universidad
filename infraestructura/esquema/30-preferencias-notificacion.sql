CREATE TABLE IF NOT EXISTS preferencia_notificacion (
    sujeto_google      text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    categoria          text NOT NULL CHECK (categoria IN ('solicitudes_matricula')),
    correo_habilitado  boolean NOT NULL DEFAULT false,
    actualizado_en     timestamp with time zone NOT NULL DEFAULT now(),
    PRIMARY KEY (sujeto_google, categoria)
);

CREATE INDEX IF NOT EXISTS preferencia_notificacion_correo_activo
    ON preferencia_notificacion (categoria, sujeto_google)
    WHERE correo_habilitado;
