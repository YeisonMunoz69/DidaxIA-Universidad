\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO.
--
-- Este archivo está en UTF-8. `psql` en Windows supone WIN1252 salvo que se le
-- diga, y al encontrar el primer acento aborta con «character with byte sequence
-- 0x8f in encoding "WIN1252" has no equivalent in encoding "UTF8"». Con
-- `ON_ERROR_STOP=1` eso deja el esquema a medias, que fue lo que ocurrió el
-- 2026-08-06: la tabla no llegó a crearse y catorce pruebas fallaron después
-- señalando al adaptador, que no tenía nada que ver.
--
-- `\encoding` es una orden de psql, no SQL: la procesa el cliente y **no viaja
-- al servidor**, de modo que funciona aun antes de que la codificación esté
-- acordada. Va delante de todo, incluidos los comentarios: psql acumula las
-- líneas de comentario y las envía junto a la primera sentencia, así que un
-- comentario con acentos por encima de esta línea reproduciría el fallo.
--
-- Es el cuarto tropiezo de codificación que este proyecto registra, y los cuatro
-- en el mismo sitio: la frontera entre dos procesos.

-- Esquema del corpus · S7 y S8
-- ============================
--
-- Solo las entidades que el incremento 2 necesita. **No es el esquema completo**:
-- las catorce entidades de datos se vuelcan en la sesión PM-V02 del plan
-- maestro, y su diseño ya existe —nombre exacto y atributos mínimos— en
-- `../../../../OE2-Arquitectura/04-Especificacion-de-Diagramas.md`.
--
-- ⚠️ ESTE ARCHIVO NO ESTÁ EN `inicio-base/`, Y ES DELIBERADO.
-- Lo de allí se ejecuta una sola vez, al crear el volumen. Un esquema tiene que
-- poder aplicarse a una base que ya existe, y la evolución del esquema **no está
-- decidida** —es la sesión PM-V01—. Mientras tanto se aplica a mano y se deja
-- escrito que se aplicó.
--
-- Aplicar · el procedimiento está en `../LEEME.md`, y se resume así:
--
--     docker compose -f OE3-Implementacion\codigo\compose.yaml exec -T base `
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/01-corpus.sql
--
-- **Se aplica con el psql DEL CONTENEDOR y no con uno instalado en el equipo.**
-- No es una preferencia: quien clone el proyecto puede no tener PostgreSQL
-- instalado, y no debería necesitarlo. La imagen ya trae el cliente, con la
-- versión que casa con el servidor, y `../LEEME.md` explica el montaje.
--
-- `ON_ERROR_STOP=1` no es opcional: sin él psql sigue tras un error y termina
-- informando éxito con el esquema a medias, que es la clase de fallo silencioso
-- que este proyecto lleva registrado cuatro veces.

BEGIN;

-- ---------------------------------------------------------------------------
-- Dominios: las listas cerradas del dominio, también en la base
-- ---------------------------------------------------------------------------
-- El dominio ya valida esto en `Fragmento.validar()`. Repetirlo aquí no es
-- duplicación ociosa: es el mismo argumento por el que `ADR-004` eligió este
-- motor —«la base rechaza físicamente», no «la aplicación se acuerda de
-- comprobar»—. Un fragmento cargado por un guion de una sola vez, o a mano
-- durante una migración, no pasa por el dominio.
--
-- Si estas listas y las del dominio divergen, la base gana y el fallo se ve al
-- insertar. Es preferible a que gane el silencio.

CREATE DOMAIN nivel_apos AS text
    CHECK (VALUE IN ('accion', 'proceso', 'objeto', 'esquema'));

CREATE DOMAIN registro_duval AS text
    CHECK (VALUE IN ('algebraico', 'grafico', 'numerico', 'verbal'));

CREATE DOMAIN modo_de_captura AS text
    CHECK (VALUE IN ('nativa', 'mixta', 'ocr', 'manual'));

-- Clave de obra de `corpus/FUENTES.md`: tres mayúsculas. El catálogo de obras
-- vive en ese archivo y no aquí — se referencia, no se copia.
CREATE DOMAIN clave_de_obra AS text
    CHECK (VALUE ~ '^[A-Z]{3}$');


-- ---------------------------------------------------------------------------
-- Fragmento del corpus
-- ---------------------------------------------------------------------------

CREATE TABLE fragmento (
    identificador       text PRIMARY KEY,
    texto               text NOT NULL CHECK (btrim(texto) <> ''),

    -- Los tres metadatos que la revisión exige anotar. `RF-COR-01` y `RF-COR-02`.
    nivel_apos          nivel_apos     NOT NULL,
    registro_duval      registro_duval NOT NULL,
    -- Del catálogo `M01`–`M24`, cerrado. Nulo si el fragmento no remedia
    -- ninguna concepción errónea: es opcional por diseño, no por descuido.
    concepcion_asociada text CHECK (concepcion_asociada ~ '^M(0[1-9]|1[0-9]|2[0-4])$'),
    nodo_grafo          text,

    -- Procedencia · `DD-15`. Las tres NOT NULL, y esto es la decisión:
    -- «un corpus sin procedencia no se puede depurar, solo borrar entero».
    -- Que sea obligatoria en la base y no solo en el dominio es lo que hace que
    -- la retirada selectiva siga siendo posible dentro de dos años.
    obra                clave_de_obra   NOT NULL,
    pagina              integer         NOT NULL CHECK (pagina >= 1),
    -- `DD-21` · página aproximada. NULL significa que `pagina` es EXACTA; con
    -- valor, el fragmento está en algún punto del rango. Se distingue en el
    -- esquema y no solo en la aplicación porque es la diferencia entre poder
    -- citar una página en el documento de grado y no poder — y un número sin
    -- saber si es exacto o estimado no se puede citar de ninguna de las dos
    -- formas.
    pagina_hasta        integer         CHECK (pagina_hasta IS NULL
                                               OR pagina_hasta >= pagina),
    captura             modo_de_captura NOT NULL DEFAULT 'mixta',

    -- Representación densa. 768 dimensiones porque es el `hidden_size` que
    -- declara el `config.json` de `intfloat/multilingual-e5-base`, que es el
    -- modelo que E01 validó y que la guía de reutilización marca como lo que
    -- **no se toca**.
    --
    -- ⚠️ La dimensión queda fijada aquí. Cambiar de modelo obliga a reconstruir
    -- la columna y el índice; no es grave y sí es trabajo, y conviene saber que
    -- se está decidiendo. Nula mientras el fragmento no se haya codificado: un
    -- fragmento puede existir en el corpus antes de entrar al índice.
    representacion      vector(768),

    -- `DD-02` exige verificar la matemática AL INGERIR. Ningún fragmento
    -- debería entrar al índice sin ello, y hoy la comprobación no está hecha ni
    -- para los que ya existen. Se registra en vez de suponerse: mientras sea
    -- falso, la consulta de recuperación puede excluirlos y la decisión de
    -- excluirlos o no queda a la vista.
    matematica_verificada boolean NOT NULL DEFAULT false,

    cargado_en          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE fragmento IS
    'Unidad del corpus. El corte es por unidad pedagógica —teorema, ejemplo, '
    'observación— y no cada N páginas: ver FORMATO-DEL-CORPUS.md §3.';

COMMENT ON COLUMN fragmento.pagina IS
    'La de la edición impresa, NO la hoja del archivo. En SWO difieren en 17.';

COMMENT ON COLUMN fragmento.pagina_hasta IS
    'NULL = la página es exacta. Con valor = aproximada, dentro del rango. DD-21.';


-- ---------------------------------------------------------------------------
-- Índices
-- ---------------------------------------------------------------------------

-- Recuperación filtrada por nodo activo · `RF-RAG-09` y la tensión `T5`:
-- el grafo enruta y el índice no crece con él.
CREATE INDEX fragmento_por_nodo ON fragmento (nodo_grafo)
    WHERE nodo_grafo IS NOT NULL;

-- Búsqueda por similitud. HNSW y no IVFFlat: IVFFlat necesita entrenarse con
-- datos ya cargados y se degrada si el corpus crece después, que es exactamente
-- lo que va a pasar aquí —hoy hay un puñado de fragmentos y se irán añadiendo
-- por tandas—. HNSW no tiene esa condición.
--
-- `vector_cosine_ops` porque `ADR-006` fija el umbral en **coseno** ≥0,70. Con
-- otra clase de operador el índice no se usaría en la consulta y el umbral
-- mediría otra cosa sin avisar.
CREATE INDEX fragmento_por_similitud ON fragmento
    USING hnsw (representacion vector_cosine_ops);

COMMIT;
