-- Invitaciones previas a cuentas institucionales · Fase 8
-- Aditiva e idempotente. El correo permite enlazar el primer inicio verificado;
-- el secreto del enlace nunca se conserva, sólo su SHA-256.

CREATE TABLE IF NOT EXISTS invitacion_rol (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correo          text NOT NULL CHECK (lower(correo) ~ '^[^@[:space:]]+@unimayor\.edu\.co$'),
    rol             text NOT NULL CHECK (rol IN ('docente', 'investigador_administrador')),
    token_huella    text NOT NULL UNIQUE CHECK (token_huella ~ '^[0-9a-f]{64}$'),
    emitida_por     text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    emitida_en      timestamp with time zone NOT NULL DEFAULT now(),
    expira_en       timestamp with time zone NOT NULL,
    estado          text NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente', 'aceptada', 'revocada', 'expirada')),
    aceptada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    aceptada_en     timestamp with time zone,
    revocada_por    text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    revocada_en     timestamp with time zone,
    CONSTRAINT invitacion_expiracion_posterior CHECK (expira_en > emitida_en),
    CONSTRAINT invitacion_aceptacion_completa
        CHECK ((aceptada_por IS NULL) = (aceptada_en IS NULL)),
    CONSTRAINT invitacion_revocacion_completa
        CHECK ((revocada_por IS NULL) = (revocada_en IS NULL)),
    CONSTRAINT invitacion_estado_coherente CHECK (
        (estado = 'pendiente' AND aceptada_en IS NULL AND revocada_en IS NULL)
        OR (estado = 'aceptada' AND aceptada_en IS NOT NULL AND revocada_en IS NULL)
        OR (estado = 'revocada' AND revocada_en IS NOT NULL AND aceptada_en IS NULL)
        OR (estado = 'expirada' AND aceptada_en IS NULL AND revocada_en IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS invitacion_rol_pendiente_unica
    ON invitacion_rol (lower(correo), rol)
    WHERE estado = 'pendiente';

CREATE INDEX IF NOT EXISTS invitacion_rol_por_estado
    ON invitacion_rol (estado, expira_en, emitida_en DESC, id DESC);

COMMENT ON TABLE invitacion_rol IS
    'Invitaciones institucionales previas. Conserva historia y sólo la huella del token.';
