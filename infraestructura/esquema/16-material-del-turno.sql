\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Mismo aviso que en las
-- catorce migraciones anteriores.

-- 16-material-del-turno.sql · material que ESTE turno recuperó · Fase 5 · paquete 5B
-- ============================================================================
--
-- QUÉ SE GUARDABA HASTA HOY, Y POR QUÉ NO BASTA
-- ---------------------------------------------------------------------------
-- `06-historial-cuerpo.sql` añadió `procedencia_referencia` a `historial_turno`:
-- una columna de texto con los identificadores separados por comas —
-- «F-001, F-014, F-252». Sirvió para contestar «¿esta respuesta tenía respaldo
-- del corpus?», que era la pregunta de entonces.
--
-- La Fase 5 hace otras tres que esa columna no contesta:
--
--   · ¿en qué ORDEN se recuperaron? Una cadena conserva el orden por accidente,
--     y basta que alguien la reordene al mostrarla para perderlo;
--   · ¿QUÉ RELACIÓN tiene cada fragmento con la respuesta? Recuperado para el
--     turno no es lo mismo que citado literalmente ni que respaldar una
--     afirmación concreta, y el encargo prohíbe expresamente presentar lo uno
--     como lo otro;
--   · ¿con qué PUNTUACIÓN entró? `ADR-006` U5 dejó escrito que la calibración
--     del umbral necesita esa distribución, y hoy sólo vive en la traza.
--
-- Una cadena no puede llevar tres datos por elemento. Esta tabla sí.
--
-- POR QUÉ NO SE BORRA LA COLUMNA VIEJA
-- ---------------------------------------------------------------------------
-- Porque hay filas escritas con ella y **no se les puede inventar un orden ni
-- una relación**. Los turnos anteriores a esta migración conservan su cadena y
-- se leen tal cual; los nuevos escriben las dos cosas. Quien lee distingue por
-- si hay filas en esta tabla, no por una fecha.
--
-- Borrar la columna habría exigido migrar los datos viejos, y migrarlos habría
-- exigido decidir qué relación tenía cada fragmento de un turno que ocurrió
-- antes de que la relación existiera. La respuesta honesta es «no consta», y la
-- forma de escribirla es no tener fila.
--
-- POR QUÉ TABLA Y NO JSONB · el mismo argumento de la migración 06
-- ---------------------------------------------------------------------------
-- `ON DELETE CASCADE` hace estructural la supresión de `RD-22`: borrar el
-- mensaje se lleva su material, sin ninguna llamada nueva que alguien tenga que
-- acordarse de añadir. Y «cuántos turnos se apoyaron en esta obra» es una
-- pregunta del OE4 que un documento opaco no contesta sin recorrerlo entero.
--
-- QUÉ NO GUARDA ESTA TABLA
-- ---------------------------------------------------------------------------
-- **El texto del fragmento.** Vive en `contenido/corpus/fragmentos/`, que es
-- contenido versionado, y copiarlo aquí crearía una segunda copia que el día
-- que `DD-15` obligue a retirar una obra habría que perseguir dentro de la base
-- de datos. Se guarda el identificador; el texto se resuelve al leer, y si la
-- obra dejó de estar autorizada el lector lo dice en vez de servirlo.
--
-- Ésa es la propiedad que el encargo pide con estas palabras: «fragmento
-- retirado después de quedar en historial · evidencia histórica conservada sin
-- permitir descarga». La evidencia es la fila; la descarga la decide la puerta.
--
-- APLICAR · no ocurre solo:
--
--     docker exec -i agente-calculo-base-prod \
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/16-material-del-turno.sql
--
-- IDEMPOTENTE Y SIN PURGA: una tabla nueva con IF NOT EXISTS. No toca ninguna
-- columna existente y no borra nada.

BEGIN;

CREATE TABLE IF NOT EXISTS historial_material (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- La cascada es la decisión, no un detalle. Ver la migración 06.
    historial   bigint NOT NULL REFERENCES historial_turno (id) ON DELETE CASCADE,

    -- Posición en la que el recuperador lo devolvió. El orden es información:
    -- el primero es el más parecido a la consulta, y mostrarlos revueltos
    -- cambiaría lo que el estudiante entiende por «lo más pertinente».
    orden       integer NOT NULL CHECK (orden >= 0),

    -- El identificador catalogado, `F-001`. La forma se comprueba aquí además
    -- de en Python: una fila escrita por SQL crudo tiene que cumplir lo mismo.
    fragmento   text NOT NULL CHECK (fragmento ~ '^F-[0-9]{3}$'),

    -- La clave de obra, para poder preguntar por obra sin leer el corpus y —
    -- sobre todo— para saber a qué puerta de publicación corresponde una fila
    -- histórica aunque el fragmento haya dejado de existir.
    obra        text NOT NULL CHECK (obra ~ '^[A-Z]{3}$'),

    -- ⚠️ EL CAMPO POR EL QUE EXISTE ESTA TABLA.
    --
    -- `recuperado` es lo único que el motor de hoy puede afirmar: el filtro 5
    -- pidió al corpus y estos fragmentos entraron al contexto del prompt. NO
    -- dice que la respuesta los use, ni que una frase concreta se apoye en uno.
    --
    -- Los otros tres valores existen para que el contrato admita trazabilidad
    -- fina el día que el sistema la produzca, y **no se escriben todavía**.
    -- Escribir `respaldo_de_afirmacion` sin un mapeo real sería exactamente la
    -- afirmación que el encargo prohíbe: «nunca afirmes respaldo por oración
    -- cuando sólo existe asociación general del turno».
    relacion    text NOT NULL DEFAULT 'recuperado'
                CHECK (relacion IN (
                    'recuperado',
                    'soporte_del_turno',
                    'cita_literal',
                    'respaldo_de_afirmacion'
                )),

    -- La similitud con la que entró, cuando el recuperador la reporta. NULL es
    -- «no consta» —un índice que no puntúa, o un doble de pruebas— y no se
    -- sustituye por cero, que significaría «no se parecía en nada».
    similitud   real CHECK (similitud IS NULL OR (similitud >= 0 AND similitud <= 1)),

    -- Dos posiciones iguales en el mismo mensaje harían el orden indefinido.
    UNIQUE (historial, orden),

    -- ⚠️ IDEMPOTENCIA FRENTE A REINTENTOS. El encargo pide expresamente que un
    -- reintento no duplique. Un mismo fragmento no puede aparecer dos veces en
    -- el material de un mensaje: si apareciera, el lector mostraría la misma
    -- fuente repetida y los recuentos del OE4 contarían de más.
    UNIQUE (historial, fragmento)
);

-- PostgreSQL no indexa las claves foráneas solo. Sin esto, reconstruir un hilo
-- recorre la tabla entera, y borrar una fila del historial también.
CREATE INDEX IF NOT EXISTS historial_material_por_mensaje
    ON historial_material (historial);

-- «Cuántos turnos se apoyaron en esta obra» y «qué se recuperó de la obra que
-- hay que retirar» son las dos consultas del OE4 y de `DD-15` que justifican
-- este índice. Sin él, retirar una obra recorre el historial completo.
CREATE INDEX IF NOT EXISTS historial_material_por_obra
    ON historial_material (obra);

COMMENT ON TABLE historial_material IS
    'Fase 5: los fragmentos que el turno recupero, con su orden y su relacion. No guarda el texto: vive en el corpus versionado.';
COMMENT ON COLUMN historial_material.relacion IS
    'recuperado es lo unico que el motor afirma hoy. Los otros tres valores esperan a que exista trazabilidad por afirmacion.';

COMMIT;
