\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Mismo aviso que en los
-- cinco esquemas anteriores.

-- Lo que el estudiante VIO, no solo lo que se narró · PM-B25 · PM-B37
-- ============================================================================
--
-- EL FALLO QUE ESTAS DOS TABLAS CIERRAN, Y YA HABÍA OCURRIDO
-- ---------------------------------------------------------------------------
-- `05-historial.sql` guarda `contenido`: la NARRACIÓN. Pero lo que llega a la
-- pantalla es un `CuerpoTurno` con bloques, y cada bloque lleva un **sello**
-- —`verificado` o `generado`, `ADR-014` §5.1— que dice si esa matemática la
-- comprobó el motor simbólico o la escribió el modelo.
--
-- Un hilo sin sellos pierde la única garantía pedagógica del sistema. Y la
-- narración lleva marcas `{{c1}}` que sin su expresión NO SE PUEDEN RENDERIZAR:
-- el sidebar de `PM-F20` mostraría la marca cruda.
--
-- ⚠️ Eso ya pasó. `http/turno.py` lo narra: hasta el 2026-08-11 el piso emitía
-- la narración tal cual y **el estudiante veía «Fíjate en {{c1}}» en pantalla**.
-- `PM-B25` lo corrigió allí. El historial lo reintrodujo el 2026-08-18, con el
-- aviso escrito veinte líneas encima del sitio donde se repitió.
--
-- POR QUÉ TABLAS Y NO UNA COLUMNA JSON
-- ---------------------------------------------------------------------------
-- Decidido el 2026-08-18. Una columna `jsonb` habría bastado para renderizar,
-- pero estas dos tablas dan algo que un documento opaco no da: **la supresión
-- de `RD-22` deja de depender de que alguien se acuerde**. `ON DELETE CASCADE`
-- la hace estructural — borrar la fila del historial se lleva sus bloques y sus
-- citas, y no hay ninguna llamada nueva que olvidar. Todo el Bloque A salió de
-- un almacén al que la cascada no llegaba; aquí no puede pasar.
--
-- Y se puede preguntar por el sello: «cuántos bloques verificados vio este
-- grupo» es una pregunta del OE4 que un documento JSON no contesta sin
-- recorrerlo entero.
--
-- APLICAR · no ocurre solo:
--
--     docker exec -i agente-calculo-base-prod \
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/06-historial-cuerpo.sql
--
-- IDEMPOTENTE Y SIN PURGA: tablas nuevas y columnas con IF NOT EXISTS.

BEGIN;

CREATE TABLE IF NOT EXISTS historial_bloque (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- ON DELETE CASCADE es la decisión, no un detalle: `RD-22` se cumple por
    -- la forma de la tabla y no por una llamada que alguien tenga que añadir.
    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    -- Posición dentro del cuerpo. El orden importa: una narración partida en
    -- bloques leída al revés no dice lo mismo.
    orden       integer NOT NULL CHECK (orden >= 0),

    tipo        text NOT NULL CHECK (btrim(tipo) <> ''),
    contenido   text NOT NULL CHECK (btrim(contenido) <> ''),

    -- `ADR-014` §5.1: dos valores y no hay un tercero. Es el campo por el que
    -- existen estas tablas.
    sello       text NOT NULL CHECK (sello IN ('verificado', 'generado')),

    -- §5, accesibilidad. `Bloque.__post_init__` ya lo exige en el borde; este
    -- CHECK es su otra mitad, para que no entre por otra vía.
    alternativo text,

    UNIQUE (historial, orden),
    CONSTRAINT historial_bloque_alternativo_obligatorio
        CHECK (tipo NOT IN ('notacion', 'grafica') OR btrim(coalesce(alternativo, '')) <> '')
);

CREATE TABLE IF NOT EXISTS historial_cita (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    -- La marca tal como aparece dentro del texto, sin las llaves: `c1`.
    marca       text NOT NULL CHECK (btrim(marca) <> ''),
    expresion   text NOT NULL CHECK (btrim(expresion) <> ''),

    -- Dos expresiones distintas bajo la misma marca en el mismo mensaje harían
    -- irresoluble la sustitución.
    UNIQUE (historial, marca)
);

-- PostgreSQL NO indexa las claves foráneas solo. Sin esto, reconstruir un hilo
-- recorre las tablas enteras, y borrar una fila del historial también.
CREATE INDEX IF NOT EXISTS historial_bloque_por_mensaje ON historial_bloque (historial);
CREATE INDEX IF NOT EXISTS historial_cita_por_mensaje   ON historial_cita   (historial);

-- Escalares del mensaje: no merecen tabla propia y contestan «¿esta respuesta
-- tenía respaldo del corpus?», que es una pregunta del OE4.
ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS nivel                   text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS procedencia_origen      text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS procedencia_referencia  text NOT NULL DEFAULT '';

COMMENT ON TABLE historial_bloque IS
    'PM-B25: lo que el estudiante vio, con su sello (ADR-014 5.1). Se borra en cascada con su mensaje.';
COMMENT ON TABLE historial_cita IS
    'ADR-014 5.4: las expresiones que la narracion menciona con marcas. Sin esto el hilo no se puede renderizar.';

COMMIT;
