CREATE TABLE IF NOT EXISTS reporte_usuario (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reportado_por       text NOT NULL REFERENCES persona(sujeto_google) ON DELETE CASCADE,
    rol_reportante      text NOT NULL CHECK (rol_reportante IN ('estudiante', 'docente', 'investigador')),
    categoria           text NOT NULL CHECK (categoria IN (
        'funcional', 'visual', 'accesibilidad', 'rendimiento', 'contenido', 'otro'
    )),
    titulo              varchar(120) NOT NULL CHECK (btrim(titulo) <> ''),
    descripcion         varchar(4000) NOT NULL CHECK (btrim(descripcion) <> ''),
    pasos               varchar(3000) NOT NULL DEFAULT '',
    ruta                varchar(240) NOT NULL CHECK (ruta LIKE '/%' AND ruta NOT LIKE '%?%'),
    estado              text NOT NULL DEFAULT 'nuevo'
                              CHECK (estado IN ('nuevo', 'en_revision', 'resuelto', 'descartado')),
    captura             bytea,
    captura_tipo        text,
    captura_sha256      char(64),
    captura_bytes       integer CHECK (captura_bytes > 0 AND captura_bytes <= 3145728),
    respuesta           varchar(2000) NOT NULL DEFAULT '',
    creado_en           timestamp with time zone NOT NULL DEFAULT now(),
    actualizado_en      timestamp with time zone NOT NULL DEFAULT now(),
    resuelto_por        text REFERENCES persona(sujeto_google),
    resuelto_en         timestamp with time zone,
    CONSTRAINT reporte_captura_completa CHECK (
        (captura IS NULL AND captura_tipo IS NULL AND captura_sha256 IS NULL AND captura_bytes IS NULL)
        OR
        (captura IS NOT NULL AND captura_tipo = 'image/webp'
         AND captura_sha256 IS NOT NULL AND captura_bytes = octet_length(captura))
    ),
    CONSTRAINT reporte_resolucion_coherente CHECK (
        (estado IN ('nuevo', 'en_revision') AND resuelto_por IS NULL AND resuelto_en IS NULL)
        OR
        (estado IN ('resuelto', 'descartado') AND resuelto_por IS NOT NULL AND resuelto_en IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS reporte_usuario_por_estado
    ON reporte_usuario (estado, creado_en DESC, id DESC);

CREATE INDEX IF NOT EXISTS reporte_usuario_por_reportante
    ON reporte_usuario (reportado_por, creado_en DESC, id DESC);
