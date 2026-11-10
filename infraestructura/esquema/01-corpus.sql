\encoding UTF8

BEGIN;

CREATE DOMAIN nivel_apos AS text
    CHECK (VALUE IN ('accion', 'proceso', 'objeto', 'esquema'));

CREATE DOMAIN registro_duval AS text
    CHECK (VALUE IN ('algebraico', 'grafico', 'numerico', 'verbal'));

CREATE DOMAIN modo_de_captura AS text
    CHECK (VALUE IN ('nativa', 'mixta', 'ocr', 'manual'));

CREATE DOMAIN clave_de_obra AS text
    CHECK (VALUE ~ '^[A-Z]{3}$');

CREATE TABLE fragmento (
    identificador       text PRIMARY KEY,
    texto               text NOT NULL CHECK (btrim(texto) <> ''),

    nivel_apos          nivel_apos     NOT NULL,
    registro_duval      registro_duval NOT NULL,

    concepcion_asociada text CHECK (concepcion_asociada ~ '^M(0[1-9]|1[0-9]|2[0-4])$'),
    nodo_grafo          text,

    obra                clave_de_obra   NOT NULL,
    pagina              integer         NOT NULL CHECK (pagina >= 1),

    pagina_hasta        integer         CHECK (pagina_hasta IS NULL
                                               OR pagina_hasta >= pagina),
    captura             modo_de_captura NOT NULL DEFAULT 'mixta',

    representacion      vector(768),

    matematica_verificada boolean NOT NULL DEFAULT false,

    cargado_en          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX fragmento_por_nodo ON fragmento (nodo_grafo)
    WHERE nodo_grafo IS NOT NULL;

CREATE INDEX fragmento_por_similitud ON fragmento
    USING hnsw (representacion vector_cosine_ops);

COMMIT;
