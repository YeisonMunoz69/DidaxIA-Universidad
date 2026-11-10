\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Mismo aviso que en
-- 01-corpus.sql, 02-modelo-estudiante.sql y 03-registro-turno.sql: es el
-- cuarto tropiezo de codificación que este proyecto registró, y los cuatro
-- en la misma frontera entre procesos.

-- La clave por la que se BORRA, no solo por la que se escribió · DD-27 · D-29
-- ============================================================================
--
-- `DD-27` (2026-08-18), literal: «un almacén cuya clave de escritura difiere
-- de su clave de supresión es un almacén que no se puede suprimir».
--
-- `registro_turno` se escribía por `identificador_sesion` y `RD-22` se ejerce
-- por SUJETO (`sujeto_de()`, `adaptadores/entrantes/http/sesiones.py:146`): un
-- estudiante autenticado con Google acumula varias sesiones bajo el mismo
-- `identificador_estable`, y no existe en ningún almacén persistente la
-- correspondencia sujeto → sesiones — las sesiones viven en memoria del
-- proceso y solo conocen las vivas. Sin esta columna, borrar por sujeto no
-- encuentra nada, y `RD-22` queda incumplido por forma, no por implementación.
--
-- LA PURGA, Y POR QUÉ NO LLEVA `DEFAULT`
-- ---------------------------------------------------------------------------
-- `ADD COLUMN ... NOT NULL` sin `DEFAULT` falla sobre una tabla con filas. Y
-- las filas anteriores a esta migración **no se pueden reparar**: su sujeto es
-- irrecuperable, porque la correspondencia vivía en memoria y se perdió en
-- cada reinicio. Son filas que nunca podrían borrarse por sujeto.
--
-- `D-29` (`DECISIONES-2026-08-18.md`) resuelve el punto y la purga está
-- confirmada: son datos de prueba de los propios autores, el directorio de
-- archivos está en `.gitignore:32` y `git ls-files` sobre él devuelve 0. La
-- alternativa —`DEFAULT ''` en silencio— es la que el acta prohíbe
-- expresamente: abriría una excepción permanente que nadie recordaría.
--
-- ESTE GUION DECLARA LA CUENTA DE LO QUE PURGA. Es un `RAISE NOTICE`, no un
-- comentario: la cifra sale por pantalla al aplicarlo y se puede pegar como
-- evidencia, en vez de quedar como algo que alguien recuerda haber visto.
--
-- ⚠️ LOS ARCHIVOS JSON NO LOS BORRA ESTE GUION. La fila referencia un archivo
-- en `ruta_archivo` y SQL no alcanza el disco. Al aplicar esto quedan archivos
-- huérfanos y hay que retirarlos aparte — el comando está abajo.
--
-- ⚠️ IDEMPOTENTE, Y LA PURGA VA GUARDADA. El bloque `DO` solo purga si la
-- columna todavía NO existe. Aplicar este guion dos veces no vuelve a borrar
-- nada: la segunda vez avisa y no toca las filas. Sin esa guarda, reaplicarlo
-- sobre una base ya migrada destruiría datos buenos.
--
-- APLICAR · ninguna de estas cosas ocurre sola. `iniciar-todo.ps1` no ejecuta
-- ningún .sql, `inicio-base/` solo corre al crear el volumen, y `esquema/`
-- solo se monta. Y HAY DOS BASES, con volúmenes distintos:
--
--   producción · agente-calculo-base-prod   (volumen agente-calculo-datos-prod)
--   desarrollo · agente-calculo-base        (volumen agente-calculo-datos)
--
--     docker exec -i agente-calculo-base-prod `
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/04-registro-turno-sujeto.sql
--     docker exec agente-calculo-backend-prod `
--         sh -c 'rm -f /app/infraestructura/registro_turnos/*.json'
--
-- Aplicar en LAS DOS, o divergen. En desarrollo, además, los archivos viven en
-- el árbol: OE3-Implementacion/codigo/infraestructura/registro_turnos/.

BEGIN;

DO $$
DECLARE
    filas_purgadas bigint;
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name   = 'registro_turno'
           AND column_name  = 'identificador_sujeto'
    ) THEN
        RAISE NOTICE
            '04-registro-turno-sujeto · la columna ya existe: NO se purga nada.';
    ELSE
        SELECT count(*) INTO filas_purgadas FROM registro_turno;
        DELETE FROM registro_turno;
        RAISE NOTICE
            '04-registro-turno-sujeto · purgadas % filas previas a la migracion (D-29). Sus archivos JSON quedan huerfanos: retirarlos aparte.',
            filas_purgadas;
    END IF;
END
$$;

-- Sin `DEFAULT`, a propósito: ver arriba. Es posible porque la purga deja la
-- tabla vacía. El `CHECK` es el mismo que ya lleva `identificador_sesion` en
-- `03-registro-turno.sql:31` — una cadena en blanco es tan insuprimible como
-- un nulo, y `NOT NULL` por sí solo no la detiene.
ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS identificador_sujeto text NOT NULL
        CHECK (btrim(identificador_sujeto) <> '');

-- RD-22: encontrar todo lo de un SUJETO para poder borrarlo en cascada. El
-- índice por sesión de `03-registro-turno.sql:42` se conserva: sigue siendo la
-- clave por la que se agrupa un hilo, solo que ya no es la de supresión.
CREATE INDEX IF NOT EXISTS registro_turno_por_sujeto
    ON registro_turno (identificador_sujeto);

COMMENT ON COLUMN registro_turno.identificador_sujeto IS
    'DD-27 (2026-08-18): la clave por la que RD-22 borra. identificador_estable de PM-B15 cuando la sesion se autentico con Google, el de sesion cuando no. Lo resuelve sujeto_de().';

COMMIT;
