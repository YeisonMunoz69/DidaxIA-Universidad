\encoding UTF8
-- ↑ LA PRIMERA LÍNEA, Y TIENE QUE SEGUIR SIÉNDOLO. Mismo aviso que en las
-- dieciséis migraciones anteriores.

-- 17-contexto-de-uso.sql · para qué se usó el tutor · EQ-031 · Fase 7 · 7A-P
-- ============================================================================
--
-- QUÉ DECIDE EQ-031, Y POR QUÉ NO BASTA CON UNA GUARDA
-- ---------------------------------------------------------------------------
-- `EQ-031` (Yeison, 2026-09-06) concede a docente e investigador un modo Tutor
-- con las herramientas del estudiante, y excluye ese uso de «matrícula,
-- evaluación estudiantil, vectores conductuales o afectivos, inferencias,
-- alertas, supervisión docente, KPI, conjuntos de investigación y
-- entrenamiento». Y añade la frase que obliga a esta columna:
--
--   «una preferencia guardada sólo en el frontend no basta: la API debe derivar
--    la elegibilidad desde el rol autenticado, **persistir el contexto** y
--    aplicar la exclusión en cada productor de señales y agregados»
--
-- Sin una columna, excluir esos turnos exigiría preguntar HOY por el rol de
-- quien los escribió. Eso es exactamente lo que no se puede hacer: un rol se
-- otorga y se revoca (`EQ-023`), así que la misma consulta daría respuestas
-- distintas según cuándo se ejecute, y un docente que dejara de serlo vería sus
-- consultas de hace un semestre convertirse en actividad de estudiante.
--
-- **El contexto es del turno, no de la persona.** Se escribe cuando ocurre y no
-- se reinterpreta después.
--
-- POR QUÉ EL HISTÓRICO SE PUEDE RELLENAR SIN ADIVINAR NADA
-- ---------------------------------------------------------------------------
-- `DEFAULT 'aprendizaje_estudiante'` no es una suposición cómoda: hasta esta
-- migración, `POST /api/turno` exigía `acceso == habilitado`
-- (`rutas/turno.py::_rechazo_por_acceso`), y ese estado sólo lo alcanza quien
-- completó el recorrido de `EQ-020` —perfil, consentimiento y, si es menor,
-- representante—. Un docente no podía tener uno: no tiene onboarding que
-- completar, así que su turno se rechazaba con 409 o 503 antes de llegar a la
-- cadena. **Toda fila anterior es de un estudiante por construcción**, y esta
-- columna escribe lo que la puerta de entrada ya garantizaba.
--
-- Es la diferencia con `04-registro-turno-sujeto.sql`, que sí tuvo que purgar:
-- allí el dato viejo era irrecuperable —vivía en memoria del proceso— y aquí
-- es deducible del contrato que regía cuando se escribió. Por eso esta
-- migración NO BORRA NADA.
--
-- POR QUÉ COLUMNA Y NO UNA TABLA APARTE
-- ---------------------------------------------------------------------------
-- Es un escalar por fila, con dos valores, que se consulta SIEMPRE junto al
-- turno al que pertenece. Una tabla `contexto_de_turno(turno, contexto)`
-- obligaría a un `JOIN` en cada agregado y —peor— haría que olvidarlo
-- devolviera silenciosamente los turnos profesionales mezclados. Con la columna
-- en la misma fila, el filtro está donde se lee.
--
-- Va en las DOS tablas y no en una: `historial_turno` es lo que el hilo muestra
-- y lo que un KPI contaría; `registro_turno` es la fila de referencia de
-- `DD-08` y la que un conjunto de investigación recorrería. Excluir en una y
-- olvidar la otra dejaría media exclusión, que es la que no se nota.
--
-- POR QUÉ NO SE CREA NINGÚN ÍNDICE TODAVÍA
-- ---------------------------------------------------------------------------
-- Porque no hay ninguna consulta que filtrar: los KPI y la analítica de curso
-- son decisiones humanas abiertas (`DECISIONES.md` § decisiones abiertas), y un
-- índice sin consumidor es coste de escritura y deuda de mantenimiento a cambio
-- de nada. Cuando exista el primer agregado, su índice se decide con su plan de
-- consulta delante y no de memoria.
--
-- APLICAR · no ocurre solo. El servicio `migraciones` de los Compose lo aplica;
-- a mano, contra una base ya migrada:
--
--     docker exec -i agente-calculo-base-prod \
--         psql -U agente -d agente -v ON_ERROR_STOP=1 -f /esquema/17-contexto-de-uso.sql
--
-- IDEMPOTENTE Y SIN PURGA. `ADD COLUMN IF NOT EXISTS` no vuelve a tocar una
-- columna existente —ni su `DEFAULT`, ni su `CHECK`—, así que aplicarlo dos
-- veces no reescribe ninguna fila.

BEGIN;

-- `historial_turno` · lo que el hilo muestra y lo que un KPI contaría.
--
-- `NOT NULL` con `DEFAULT`: al revés que en la 04, aquí sí hay valor correcto
-- para las filas existentes (ver la cabecera), así que la columna nace completa
-- y ninguna consulta futura tiene que tratar el nulo como un tercer caso.
ALTER TABLE historial_turno
    ADD COLUMN IF NOT EXISTS contexto_de_uso text NOT NULL
        DEFAULT 'aprendizaje_estudiante'
        CHECK (contexto_de_uso IN ('aprendizaje_estudiante', 'consulta_profesional'));

-- `registro_turno` · la fila de referencia de `DD-08`.
ALTER TABLE registro_turno
    ADD COLUMN IF NOT EXISTS contexto_de_uso text NOT NULL
        DEFAULT 'aprendizaje_estudiante'
        CHECK (contexto_de_uso IN ('aprendizaje_estudiante', 'consulta_profesional'));

COMMENT ON COLUMN historial_turno.contexto_de_uso IS
    'EQ-031: para que se uso el tutor en este turno. consulta_profesional queda fuera de evaluacion, perfil, diagnostico, alertas, supervision, KPI y conjuntos de investigacion. Se deriva del rol real al crear el turno y NO se reinterpreta despues.';

COMMENT ON COLUMN registro_turno.contexto_de_uso IS
    'EQ-031: igual que en historial_turno. Va en las dos tablas porque excluir en una sola deja media exclusion.';

COMMIT;
