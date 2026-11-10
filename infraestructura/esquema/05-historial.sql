\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Mismo aviso que en los
-- cuatro esquemas anteriores: es el cuarto tropiezo de codificación que este
-- proyecto registró, y los cuatro en la misma frontera entre procesos.

-- El historial de conversación · UNA FILA POR VOZ · PM-B37 · RF-REG-01
-- ============================================================================
--
-- LA FORMA SALE DE `EntradaDeTurno`, NO AL REVÉS
-- ---------------------------------------------------------------------------
-- `dominio/puertos/registro.py::EntradaDeTurno` declara ocho campos y esta
-- tabla tiene ocho columnas. El puerto existía desde el principio y ningún
-- adaptador lo implementaba; el orden correcto es leerlo y derivar de él.
--
-- Su docstring lo dice literal: «el mismo turno produce (al menos) DOS
-- entradas, una por lado de la conversación, porque RF-REG-01 pide poder
-- reconstruir la sesión completa, y una sesión tiene dos voces».
--
-- Por eso NO hay una fila con `texto_estudiante` y `respuesta_agente` juntos:
-- colapsar las dos voces obligaría a rodear el puerto, y
-- `pruebas/arquitectura/test_reglas_arquitectonicas.py` vigila que el dominio
-- no dependa de los adaptadores (`ADR-001` §7.2). Dos turnos consecutivos de
-- una sesión producen CUATRO filas. Si producen dos, algo sobrescribe — que es
-- el fallo de `PM-V15`, y costó cuatro de cada cinco turnos la vez anterior.
--
-- ESTO ES HISTORIAL, NO UN ÍNDICE · ADR-004 C1
-- ---------------------------------------------------------------------------
-- **Sin `UPDATE`.** A diferencia de `registro_turno` —que sí usa
-- `ON CONFLICT DO UPDATE` porque es la fila de referencia de `DD-08`—, aquí no
-- se reescribe nada: lo que el estudiante escribió es lo que ocurrió. La única
-- operación que borra es la cascada de `RD-22`, y borra, no sobrescribe.
--
-- RF-REG-01 PASA A PARCIAL, NO A COMPLETO
-- ---------------------------------------------------------------------------
-- Esta es la primera vez que el sistema persiste el TEXTO del estudiante: los
-- registros de `infraestructura/registro_turnos/` guardan trazas, latencias y
-- veredictos, y ningún contenido literal. `RF-REG-01` pide «marca temporal,
-- autor y contenido literal» y esta tabla trae las tres, así que el requisito
-- pasa de no satisfecho a **parcialmente** satisfecho. Se escribe así, sin
-- redondear al alza: faltan `RF-REG-03` a `RF-REG-08`.
--
-- Y el texto va LITERAL, sin normalizar (`T-05` del acta del 2026-08-18): el
-- normalizado es del filtro 1 y ya viaja en las trazas.
--
-- LA CLAVE POR LA QUE SE BORRA · DD-27
-- ---------------------------------------------------------------------------
-- `identificador_sujeto` está desde el primer día, no añadida después. Es la
-- lección de `04-registro-turno-sujeto.sql`: aquella tabla se escribió por
-- sesión, `RD-22` se ejerce por sujeto, y la distancia entre las dos claves
-- dejó los turnos fuera de la cascada durante meses. Una superficie nueva de
-- dato personal nace cubierta o no nace.
--
-- APLICAR · no ocurre solo. `iniciar-todo.ps1` no ejecuta ningún .sql y
-- `esquema/` solo se monta:
--
--     docker exec -i agente-calculo-base-prod \
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/05-historial.sql
--
-- Desde el 2026-08-18 hay UN solo entorno en marcha —`compose.produccion.yaml`—
-- y su volumen es `agente-calculo-datos-prod`. El de desarrollo
-- (`agente-calculo-datos`) se conserva migrado: si se vuelve a levantar, hay
-- que aplicarle este esquema también, o divergen.
--
-- IDEMPOTENTE Y SIN PURGA. La tabla es nueva: no hay nada que migrar y este
-- guion NO BORRA NADA, a diferencia del 04. Aplicarlo dos veces no hace nada.

BEGIN;

CREATE TABLE IF NOT EXISTS historial_turno (
    -- Orden de inserción estable: dentro de un mismo turno, la voz del
    -- estudiante se inserta antes que la del sistema, y `momento` puede
    -- empatar al milisegundo. `id` es lo que desempata al reconstruir el hilo.
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- El MISMO `identificador_turno` que viaja al estudiante en
    -- `CuerpoTurno.turno` (`PM-V15`). Es lo que permite que un turno reportado
    -- se encuentre aquí — `RU-12`. No es único: dos filas lo comparten, una
    -- por voz, y ésa es toda la idea.
    turno                text NOT NULL CHECK (btrim(turno) <> ''),

    -- Agrupa el hilo. Es la clave de LECTURA.
    identificador_sesion text NOT NULL CHECK (btrim(identificador_sesion) <> ''),

    -- DD-27: la clave de SUPRESIÓN, que no es la misma. Ver la cabecera.
    identificador_sujeto text NOT NULL CHECK (btrim(identificador_sujeto) <> ''),

    -- RF-REG-01, marca temporal. `DEFAULT now()` es el respaldo para quien
    -- inserte sin darla; el adaptador la pasa explícita, porque el momento que
    -- importa es cuando ocurrió el turno, no cuando la ruta fría llegó a
    -- escribirlo.
    momento              timestamptz NOT NULL DEFAULT now(),

    -- RF-REG-01, autor. Dos voces y no más: la lista está en
    -- `EntradaDeTurno.AUTORES` y este CHECK es su otra mitad.
    autor                text NOT NULL CHECK (autor IN ('estudiante', 'sistema')),

    -- RF-REG-01, contenido literal. Sin normalizar (T-05).
    contenido            text NOT NULL CHECK (btrim(contenido) <> ''),

    -- T-04: si este contenido es la explicación de una degradación en vez de
    -- una respuesta. Los degradados SÍ entran —un hilo con huecos es peor—,
    -- pero entran marcados. El CHECK impide lo único que no tiene sentido:
    -- que un mensaje del estudiante figure como degradación del sistema.
    degradado            boolean NOT NULL DEFAULT false
                         CHECK (NOT degradado OR autor = 'sistema')
);

COMMENT ON TABLE historial_turno IS
    'PM-B37: el historial de conversacion, una fila por voz. Derivada de dominio/puertos/registro.py::EntradaDeTurno. Historial, no indice: sin UPDATE (ADR-004 C1).';

-- Listar las conversaciones de un titular, de la mas reciente hacia atras.
-- Es lo que sirve `GET /api/historial` (T-07.bis), y tambien la clave por la
-- que RD-22 borra: el mismo indice cubre las dos.
CREATE INDEX IF NOT EXISTS historial_turno_por_sujeto
    ON historial_turno (identificador_sujeto, momento DESC);

-- Reconstruir un hilo en orden. `id` y no `momento`: desempata las dos voces
-- del mismo turno, que pueden compartir marca temporal.
CREATE INDEX IF NOT EXISTS historial_turno_por_sesion
    ON historial_turno (identificador_sesion, id);

COMMIT;
