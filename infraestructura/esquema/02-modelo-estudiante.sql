\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Ver el mismo aviso en
-- 01-corpus.sql: es el cuarto tropiezo de codificación que este proyecto
-- registró, y todos en la misma frontera entre procesos.

-- Esquema del modelo del estudiante · S4 · PM-B11
-- ==================================================
--
-- Los tres registros de `ADR-003` §6.2 (R-A, R-C, R-E), persistidos con el
-- mecanismo que `ADR-004` §7 adoptó para C1 —«versionado sin sobrescritura»—:
-- **tres tablas, no una**, porque `ADR-003` K1 (crítico) prohíbe que
-- compartan espacio de representación, y una tabla `(sesión, dimensión,
-- valor)` repetiría en la base el error que `ADR-003` corrigió en el modelo.
--
-- Aplicar · mismo procedimiento que `01-corpus.sql`:
--
--     docker compose -f OE3-Implementacion\codigo\compose.yaml exec -T base `
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/02-modelo-estudiante.sql
--
-- ⚠️ Igual que `01-corpus.sql`, este archivo NO está en `inicio-base/`: se
-- aplica a mano sobre una base que ya existe, y queda escrito que se aplicó.

BEGIN;

-- ---------------------------------------------------------------------------
-- Identidad del sujeto del perfil
-- ---------------------------------------------------------------------------
-- `PM-B15` (identidad delegada) no existe todavía, así que hoy la única
-- identidad disponible es la de sesión. Las tres tablas usan
-- `identificador_sujeto` y no `identificador_sesion` a propósito: R-C y R-E
-- son longitudinales ENTRE sesiones (`ADR-003` §6.2 «Alcance»), y nombrar la
-- columna por lo que hoy la puebla —una sesión— habría escondido esa
-- limitación en vez de declararla. **Hoy se puebla con el identificador de
-- sesión** porque no hay nada mejor; el día que `PM-B15` exista, pasa a ser
-- el identificador institucional sin tocar el esquema.

-- ---------------------------------------------------------------------------
-- R-A · afectivo · CONTINUO, CON DECAIMIENTO → versionado por rango temporal
-- ---------------------------------------------------------------------------
-- `ADR-004` §7.1, mecanismo de C1 literal: «tabla de versiones con columna de
-- rango temporal y restricción de exclusión. La base rechaza FÍSICAMENTE dos
-- versiones vigentes del mismo registro». `btree_gist` (`infraestructura/
-- inicio-base/01-extensiones.sql`) es lo que permite mezclar `=` sobre texto
-- con `&&` sobre el rango en la misma restricción de exclusión.
--
-- El adaptador nunca hace UPDATE del contenido de una fila: al llegar una
-- observación nueva, CIERRA el rango de vigencia de la fila anterior —pone su
-- extremo abierto en `now()`— e INSERTA una fila nueva con rango abierto
-- hacia el futuro. Ese cierre no reescribe ningún valor: `valor_nuevo`,
-- `regla_aplicada`, `certeza`… de la fila cerrada quedan exactamente como se
-- escribieron. Si el adaptador tuviera un defecto y NO cerrara la anterior
-- antes de insertar, la restricción de exclusión rechaza el INSERT —eso es
-- lo que hace la sobrescritura IMPOSIBLE y no solo improbable, tal como
-- `ADR-004` lo exige.

CREATE TABLE perfil_afectivo (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),
    -- `dominio/puertos/registro.py` · SUBCOMPONENTES_AFECTIVOS. No se repite
    -- la lista aquí como CHECK cerrado porque RF-ADM-06 los declara
    -- configurables — igual que `nodo_grafo` en 01-corpus.sql no restringe
    -- contra un catálogo cerrado.
    subcomponente      text NOT NULL CHECK (btrim(subcomponente) <> ''),
    alcance            text NOT NULL CHECK (alcance IN ('estado', 'rasgo')),

    turno              text NOT NULL,
    señal              text NOT NULL,
    regla_aplicada     text NOT NULL CHECK (btrim(regla_aplicada) <> ''),
    valor_previo       real NOT NULL CHECK (valor_previo BETWEEN 0 AND 1),
    valor_nuevo        real NOT NULL CHECK (valor_nuevo BETWEEN 0 AND 1),
    lambda_aplicado    real NOT NULL CHECK (lambda_aplicado BETWEEN 0 AND 1),
    certeza            real NOT NULL CHECK (certeza BETWEEN 0 AND 1),

    -- El rango de vigencia. Abierto por arriba mientras sea la versión
    -- vigente; se cierra en `now()` cuando llega la siguiente.
    vigencia           tstzrange NOT NULL DEFAULT tstzrange(now(), NULL),

    creado_en          timestamptz NOT NULL DEFAULT now(),

    -- El mecanismo de C1, literal: nunca dos filas vigentes a la vez para el
    -- mismo (sujeto, subcomponente, alcance).
    EXCLUDE USING gist (
        identificador_sujeto WITH =,
        subcomponente        WITH =,
        alcance               WITH =,
        vigencia              WITH &&
    )
);

COMMENT ON TABLE perfil_afectivo IS
    'R-A de ADR-003 §6.2. Versionado por rango temporal, ADR-004 C1. '
    'Nunca UPDATE sobre una fila ya insertada.';

CREATE INDEX perfil_afectivo_vigente ON perfil_afectivo (identificador_sujeto, subcomponente, alcance)
    WHERE upper(vigencia) IS NULL;

-- ---------------------------------------------------------------------------
-- R-C · conceptual · MÁQUINA DE ESTADOS, NO DECAE → registro de eventos
-- ---------------------------------------------------------------------------
-- Sin decaimiento no hace falta un rango temporal para saber cuál es la
-- versión vigente: es, por definición, la última fila por `creado_en` para el
-- mismo (sujeto, elemento). El registro es puramente de anexado — ninguna
-- sentencia UPDATE existe en el adaptador para esta tabla tampoco, y aquí ni
-- siquiera hace falta una restricción de exclusión para impedirlo: no hay
-- ninguna vía de sobrescribir sin ejecutar el UPDATE que el adaptador no
-- tiene.

CREATE TABLE perfil_conceptual (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),
    -- `dominio/puertos/registro.py` documenta que NO se restringe a M01-M24:
    -- también dominio por nodo y el patrón grados↔radianes.
    elemento           text NOT NULL CHECK (btrim(elemento) <> ''),

    turno              text NOT NULL,
    estado_previo      text NOT NULL CHECK (estado_previo IN ('no_detectada', 'activa', 'remediada', 'recurrente')),
    estado_nuevo       text NOT NULL CHECK (estado_nuevo IN ('no_detectada', 'activa', 'remediada', 'recurrente')),
    evento_diagnostico text NOT NULL DEFAULT '',

    creado_en          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE perfil_conceptual IS
    'R-C de ADR-003 §6.2. Anexado puro: el estado vigente es la última fila '
    'por creado_en para (identificador_sujeto, elemento).';

CREATE INDEX perfil_conceptual_por_sujeto ON perfil_conceptual (identificador_sujeto, elemento, creado_en DESC);

-- ---------------------------------------------------------------------------
-- R-E · estratégico · CONTADOR SOBRE VENTANA → registro de eventos
-- ---------------------------------------------------------------------------
-- Misma disciplina de anexado puro que R-C. `contador` y `ciclo_negativo` son
-- el resumen que `dominio/modelo/estudiante.py` calculó EN ESE MOMENTO sobre
-- la ventana de `DD-06`; no se recalculan aquí ni se actualizan después.

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

COMMENT ON TABLE perfil_estrategico IS
    'R-E de ADR-003 §6.2. Anexado puro, ventana de DD-06 (3 episodios).';

CREATE INDEX perfil_estrategico_por_sujeto ON perfil_estrategico (identificador_sujeto, creado_en DESC);

COMMIT;
