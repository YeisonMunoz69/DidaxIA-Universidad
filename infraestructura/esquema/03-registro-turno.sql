\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Ver el mismo aviso en
-- 01-corpus.sql y 02-modelo-estudiante.sql: es el cuarto tropiezo de
-- codificación que este proyecto registró, y los cuatro en la misma
-- frontera entre procesos.

-- La fila de referencia del registro por turno · DD-08 · PM-B20
-- ==================================================================
--
-- `DD-08`, literal: «archivo estructurado, con una fila en la base que lo
-- referencia». El contenido del turno —trazas, metadatos, veredictos— vive
-- en el archivo que `adaptadores/salientes/registro/archivo.py` escribe;
-- esta tabla es solo el índice que hace posible que `RD-22` encuentre y
-- borre esos archivos por sesión, con transacción, en vez de recorrer un
-- directorio a mano.
--
-- Aplicar · mismo procedimiento que los esquemas anteriores:
--
--     docker compose -f OE3-Implementacion\codigo\compose.yaml exec -T base `
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/03-registro-turno.sql

BEGIN;

CREATE TABLE registro_turno (
    -- ✅ CORREGIDO EL 2026-08-18. Aquí decía que «sin un identificador de
    -- turno propio en `ContextoTurno`, hoy `turno` vale lo mismo que
    -- `identificador_sesion`». **Dejó de ser cierto el 2026-08-14**:
    -- `PM-V15` añadió `ContextoTurno.identificador_turno` y
    -- `dominio/filtros/registro.py` escribe desde entonces
    -- `turno = ctx.identificador_turno or ctx.identificador_sesion`.
    --
    -- Se corrige con la fecha dentro, y no borrando la frase vieja, porque un
    -- comentario que narra su historia envejece de forma visible y uno que
    -- solo afirma el estado presente envejece en silencio. Este llevaba
    -- cuatro días induciendo a error a quien leyera antes de tocar la tabla,
    -- que es justo lo que `ANTES-DE-MODIFICAR.md` pide hacer.
    --
    -- La previsión de entonces se cumplió: la clave primaria sigue siendo
    -- `turno` y la tabla no cambió de forma al llegar el identificador real.
    turno                text PRIMARY KEY,
    identificador_sesion text NOT NULL CHECK (btrim(identificador_sesion) <> ''),
    ruta_archivo         text NOT NULL CHECK (btrim(ruta_archivo) <> ''),
    nivel_divulgacion    integer NOT NULL,
    latencia_total_ms    real NOT NULL CHECK (latencia_total_ms >= 0),
    creado_en            timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE registro_turno IS
    'DD-08: fila de referencia. El contenido vive en ruta_archivo, no aquí.';

-- Agrupa el hilo. ⚠️ **No es la clave de supresión** desde el 2026-08-18:
-- `RD-22` se ejerce por SUJETO y `04-registro-turno-sujeto.sql` añade
-- `identificador_sujeto` con su propio índice. Este se conserva porque seguir
-- un hilo y borrar un titular son dos operaciones distintas (`DD-27`).
CREATE INDEX registro_turno_por_sesion ON registro_turno (identificador_sesion);

COMMIT;
