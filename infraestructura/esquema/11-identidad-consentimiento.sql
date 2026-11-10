-- ==============================================================================
-- 11-identidad-consentimiento.sql — Identidad, onboarding, consentimiento
-- versionado, asentimiento y evidencia del representante
-- EQ-016 · EQ-020 … EQ-024 · Fase 3 · sesión 2
-- ==============================================================================
--
-- Qué añade, y por qué no toca nada de lo que ya existe
-- -----------------------------------------------------------------------------
-- La Fase 3 · sesión 1 aprobó tres dimensiones SEPARADAS —consentimiento,
-- representante y asentimiento— y un acceso que se CALCULA. Nada de eso cabe en
-- `consentimiento_usuario` (`07-consentimiento-usuario.sql`), que es una fila
-- por titular con `ON CONFLICT DO UPDATE`: una tabla que sobrescribe no puede
-- sostener un historial inmutable, y una sola columna `decision` no puede
-- expresar tres dimensiones.
--
-- ⚠️ `consentimiento_usuario` permanece intacta y en uso. Este archivo no la
-- borra, no la renombra, no la transforma y no promueve ninguna de sus filas a
-- un consentimiento válido del modelo nuevo. Las rutas HTTP siguen leyéndola y
-- escribiéndola exactamente igual; cambiarlas es la sesión 3. Aquí no hay ni un
-- UPDATE, ni un DELETE, ni un INSERT que lea de ella.
--
-- Qué cambió tras la primera revisión independiente
-- -----------------------------------------------------------------------------
-- La primera versión de este archivo describía sus reglas en comentarios y las
-- dejaba a cargo del código Python. La revisión lo devolvió: un comentario no es
-- una restricción. Ahora están en la base y se comprueban con SQL crudo, sin
-- pasar por ningún adaptador:
--
--   1. **alcance** · cada dimensión sólo puede referenciar versiones de SU
--      alcance, mediante clave foránea compuesta contra `(codigo, alcance)`;
--   2. **versión requerida** · otorgar, rechazar y cargar evidencia sólo pueden
--      usar la versión que rige ahora; revocar retira la concesión efectivamente
--      otorgada aunque su texto haya vencido. Ver `didaxia_version_requerida()`
--      y `didaxia_version_del_acto()` al final del archivo (hito A2);
--   3. **categoría de edad** · el consentimiento la deriva la base desde
--      `persona` dentro de la transacción; lo que llegue del borde se descarta;
--   4. **catálogo cerrado** · las seis finalidades de `EQ-021` están en un CHECK,
--      y toda versión publicada tiene que cubrirlas;
--   5. **inmutabilidad** · versiones, finalidades de versión, eventos, evidencia
--      y revisiones rechazan UPDATE y DELETE por la conexión de la aplicación;
--   6. **asentimiento** · sólo se puede registrar sobre una persona menor;
--   7. **auditoría del rol** · revocar registra quién y cuándo, o no se guarda.
--
-- Aditivo y repetible
-- -----------------------------------------------------------------------------
-- Todo es `CREATE ... IF NOT EXISTS`, `CREATE OR REPLACE` o el único INSERT del
-- catálogo cerrado de finalidades, con `ON CONFLICT DO NOTHING`. El motor de la
-- Fase 2 · sesión 2B gobierna orden, atomicidad y checksum; este archivo no abre
-- ni cierra transacción propia (ver `catalogo.py::_sql_ejecutable`).
--
-- Qué NO hay aquí, y es deliberado
-- -----------------------------------------------------------------------------
-- - Ninguna versión de consentimiento sembrada. El texto final no existe
--   todavía (`DECISIONES.md` § Decisiones abiertas); inventar un `codigo` y una
--   `huella_contenido` habría fabricado la autorización que este esquema existe
--   para poder demostrar. `consentimiento_version` nace vacía a propósito.
-- - Ningún rol asignado. `rol_asignacion` nace vacía: sembrar los correos de
--   Yeison y Fabian metería datos personales en un archivo versionado y
--   convertiría un rol en una constante de código (`EQ-023`).
-- - Ningún PDF. La evidencia del representante vive en almacenamiento privado
--   (`EQ-021`); aquí sólo hay metadatos. No existe ninguna columna `bytea`,
--   `blob` ni `text` pensada para contener el archivo.
-- - Ninguna columna de cédula, teléfono o correo del representante (`EQ-021`,
--   explícito).
-- - Ninguna tabla de eliminación ni de mantenimiento. Pertenecen a las sesiones
--   4 y 3; el dominio ya sabe calcular esos estados a partir de datos que
--   recibirá, así que no hacen falta tablas sin consumidor.
-- - **Ningún camino de excepción para borrar.** Los disparadores de
--   inmutabilidad no consultan ninguna variable de sesión ni ningún indicador
--   que el adaptador normal pudiera activar: no hay puerta trasera. La sesión 4
--   tendrá que construir un camino explícito, separado y auditado para los datos
--   cuya eliminación sea procedente (`EQ-022`), y esa decisión no se anticipa
--   aquí.

-- ---------------------------------------------------------------------------
-- persona · la identidad estable y el perfil declarado en el onboarding
-- ---------------------------------------------------------------------------
-- La clave primaria es el sujeto de Google (`sub` del `id_token`), no el correo:
-- `DD-18` y `EQ-020` lo fijan porque el correo puede cambiar de alias y el `sub`
-- no. Es el mismo valor que hoy viaja como `identificador_estable` en la sesión
-- y que `sujeto_de()` deja en `clase_matricula.identificador`, así que
-- relacionar una persona con su clase NO exige reinterpretar ningún dato ni
-- añadir una columna aquí: el mecanismo de clase/matrícula de `08-clases.sql` ya
-- lo resuelve y se consulta en sólo lectura.
--
-- `correo` y `nombre` vienen de Google. `edad_declarada`, `programa` y
-- `semestre` los declara la persona en el onboarding (`EQ-020`). No hay teléfono
-- ni documento de identidad, y no puede haberlos sin cambiar este archivo.
--
-- `edad_declarada` admite NULL y eso NO significa «mayor de edad»: significa
-- «no declarada», que es un perfil incompleto. El dominio
-- (`dominio/modelo/identidad.py`) lo trata como tal, y el disparador que deriva
-- la categoría de edad de un consentimiento se niega a inventarla.
--
-- Esta tabla SÍ admite UPDATE: corregir un semestre mal escrito o registrar la
-- edad que la persona cumplió no es reescribir una decisión. Lo inmutable son
-- los actos, y viven en sus propias tablas.
CREATE TABLE IF NOT EXISTS persona (
    sujeto_google        text PRIMARY KEY CHECK (btrim(sujeto_google) <> ''),
    correo               text NOT NULL CHECK (position('@' in correo) > 1),
    nombre               text NOT NULL DEFAULT '',
    edad_declarada       integer CHECK (edad_declarada BETWEEN 0 AND 120),
    programa             text NOT NULL DEFAULT '',
    semestre             integer CHECK (semestre BETWEEN 1 AND 20),
    -- `EQ-016`: siete días para CARGAR la autorización del representante. Se
    -- guarda para poder mostrarla y auditarla; en esta sesión nada la hace
    -- cumplir —no hay tarea programada ni bloqueo HTTP— y por eso admite NULL.
    representante_limite timestamp with time zone,
    creada_en            timestamp with time zone NOT NULL DEFAULT now(),
    actualizada_en       timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE persona IS
    'Identidad estable (sujeto de Google) y perfil de onboarding de EQ-020. '
    'Sin telefono ni documento de identidad. La vinculacion a clase no vive '
    'aqui: la resuelve clase_matricula (08-clases.sql) por el mismo sujeto.';

-- El correo se consulta para presentar y para auditar, nunca como clave. Sin
-- UNIQUE a propósito: un cambio de alias institucional no puede romper una
-- identidad que el `sub` ya declara estable.
CREATE INDEX IF NOT EXISTS persona_por_correo ON persona (lower(correo));

-- ---------------------------------------------------------------------------
-- consentimiento_finalidad · el catálogo CERRADO de EQ-021
-- ---------------------------------------------------------------------------
-- Tabla y no `text` libre, y tampoco JSON: `EQ-021` enumera seis finalidades y
-- el encargo prohíbe guardarlas «como texto libre sin validación». Con una tabla
-- la relación versión↔finalidad tiene integridad referencial de verdad y se
-- puede consultar («qué versiones cubren investigación») sin abrir un documento.
--
-- ⚠️ El CHECK es lo que hace que «catálogo cerrado» sea cierto y no una
-- descripción. Sin él la tabla admitía cualquier texto y la palabra «catálogo»
-- era decorativa: la primera revisión lo devolvió por eso. **Añadir una séptima
-- finalidad exige editar este archivo**, es decir, una migración deliberada.
CREATE TABLE IF NOT EXISTS consentimiento_finalidad (
    codigo        text PRIMARY KEY CHECK (codigo IN (
                      'autenticacion_y_seguridad',
                      'historial_conversacional',
                      'perfil_conductual',
                      'personalizacion_pedagogica',
                      'investigacion',
                      'visualizacion_docente')),
    registrada_en timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE consentimiento_finalidad IS
    'Catalogo CERRADO de finalidades de EQ-021: el CHECK de codigo admite '
    'exactamente seis valores. No contiene el TEXTO que se muestra a la '
    'persona: ese texto pertenece a la version y todavia no existe.';

-- Las seis de `EQ-021`, ni una más. No es una versión de consentimiento: es el
-- vocabulario con el que una versión futura declarará qué cubre.
INSERT INTO consentimiento_finalidad (codigo) VALUES
    ('autenticacion_y_seguridad'),
    ('historial_conversacional'),
    ('perfil_conductual'),
    ('personalizacion_pedagogica'),
    ('investigacion'),
    ('visualizacion_docente')
ON CONFLICT (codigo) DO NOTHING;

-- ---------------------------------------------------------------------------
-- consentimiento_version · qué se firmó, no quién lo firmó
-- ---------------------------------------------------------------------------
-- `EQ-021`: el evento conserva versión, alcance, finalidades, fecha y
-- comprobante. Versión, alcance, finalidades y vigencia son de la VERSIÓN —una
-- por todas las personas— y por eso viven aquí y no repetidas en cada evento.
--
-- `huella_contenido` es el SHA-256 del texto exacto que se publicó. Es lo que
-- permite demostrar, años después, qué leyó quien aceptó. Se exige el formato,
-- no un valor: la tabla nace vacía porque el texto todavía no está aprobado.
--
-- `alcance` distingue los tres documentos que `EQ-016`/`EQ-021` describen y que
-- NO son el mismo: el consentimiento del titular, el asentimiento del menor y la
-- autorización del representante.
--
-- `UNIQUE (codigo, alcance)` es redundante como unicidad —`codigo` ya es clave
-- primaria— y **no es decorativo**: es el destino de las claves foráneas
-- compuestas de las tres dimensiones. Sin él PostgreSQL no puede exigir que un
-- consentimiento apunte a una versión de alcance `titular`, y esa exigencia
-- volvería a ser un `if` de Python.
CREATE TABLE IF NOT EXISTS consentimiento_version (
    codigo           text PRIMARY KEY CHECK (btrim(codigo) <> ''),
    alcance          text NOT NULL
                         CHECK (alcance IN ('titular', 'asentimiento', 'representante')),
    huella_contenido text NOT NULL CHECK (huella_contenido ~ '^[0-9a-f]{64}$'),
    vigente_desde    timestamp with time zone NOT NULL,
    vigente_hasta    timestamp with time zone,
    registrada_en    timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT consentimiento_version_vigencia
        CHECK (vigente_hasta IS NULL OR vigente_hasta > vigente_desde),
    CONSTRAINT consentimiento_version_codigo_alcance UNIQUE (codigo, alcance)
);

COMMENT ON TABLE consentimiento_version IS
    'Versiones publicadas del consentimiento, asentimiento y autorizacion. '
    'Nace vacia: el texto final no esta aprobado y sembrar una version '
    'inventada seria fabricar la autorizacion que este esquema audita. '
    'UNIQUE (codigo, alcance) existe para las claves foraneas compuestas.';

CREATE INDEX IF NOT EXISTS consentimiento_version_por_alcance
    ON consentimiento_version (alcance, vigente_desde DESC, codigo DESC);

-- Las finalidades que cubre cada versión. Clave compuesta: declarar dos veces la
-- misma finalidad en una versión no significa nada, y la base lo impide.
CREATE TABLE IF NOT EXISTS consentimiento_version_finalidad (
    version   text NOT NULL REFERENCES consentimiento_version (codigo) ON DELETE RESTRICT,
    finalidad text NOT NULL REFERENCES consentimiento_finalidad (codigo) ON DELETE RESTRICT,
    PRIMARY KEY (version, finalidad)
);

COMMENT ON TABLE consentimiento_version_finalidad IS
    'Que finalidades cubre cada version. ON DELETE RESTRICT en las dos claves: '
    'nada de este modelo se borra en cascada.';

-- ---------------------------------------------------------------------------
-- consentimiento_evento · el historial INMUTABLE del titular
-- ---------------------------------------------------------------------------
-- Una fila por acto: aceptar, rechazar, revocar y volver a aceptar son cuatro
-- filas, no una columna que cambia. Ningún adaptador hace UPDATE ni
-- `ON CONFLICT DO UPDATE` sobre esta tabla, y desde la corrección de la revisión
-- la base tampoco lo permite.
--
-- `pendiente` no está en el CHECK y es intencional. `pendiente` es la AUSENCIA
-- de eventos, no un evento; guardarlo crearía un estado escribible que podría
-- confundirse con una decisión tomada. Lo mismo vale para el asentimiento.
--
-- `alcance` es una columna con valor fijo, y su único trabajo es sostener la
-- clave foránea compuesta: no se elige, no se escribe desde fuera —tiene DEFAULT
-- y CHECK de un solo valor— y hace imposible que un consentimiento se apoye en
-- la versión del asentimiento o en la del representante.
--
-- `categoria_edad` la DERIVA un disparador desde `persona` dentro de la misma
-- transacción (`didaxia_derivar_categoria_edad`). Lo que llegue en el INSERT se
-- descarta: `EQ-016` hace depender el régimen de la edad, y aceptar esa
-- categoría como texto del borde habría dejado la regla en manos del cliente.
-- Es además lo que permite detectar que alguien cumplió 18 y exigirle una nueva
-- aceptación (`EQ-021`).
--
-- `id` es IDENTITY monótono y por eso la consulta del estado vigente puede ser
-- determinista aunque dos eventos compartan `momento` al microsegundo:
-- `ORDER BY momento DESC, id DESC` no admite empate.
--
-- `comprobante` es el SHA-256 del recibo de lo que la persona vio y aceptó
-- (`EQ-021`). Se exige su forma, no se calcula aquí: quien lo produce es el
-- borde, a partir del texto real presentado.
CREATE TABLE IF NOT EXISTS consentimiento_evento (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google  text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    version        text NOT NULL,
    alcance        text NOT NULL DEFAULT 'titular' CHECK (alcance = 'titular'),
    estado         text NOT NULL CHECK (estado IN ('otorgado', 'rechazado', 'revocado')),
    categoria_edad text NOT NULL CHECK (categoria_edad IN ('menor', 'adulto')),
    comprobante    text NOT NULL CHECK (comprobante ~ '^[0-9a-f]{64}$'),
    momento        timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT consentimiento_evento_version_titular
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

COMMENT ON TABLE consentimiento_evento IS
    'Historial inmutable del consentimiento del titular (EQ-016, EQ-022). Una '
    'fila por acto; los eventos anteriores nunca se actualizan ni se borran, y '
    'un disparador rechaza UPDATE y DELETE. La categoria de edad la deriva la '
    'base desde persona: no se acepta del borde.';

CREATE INDEX IF NOT EXISTS consentimiento_evento_por_sujeto
    ON consentimiento_evento (sujeto_google, momento DESC, id DESC);

-- ---------------------------------------------------------------------------
-- asentimiento_evento · la dimensión propia del menor
-- ---------------------------------------------------------------------------
-- Separada del consentimiento y de la evidencia del representante porque
-- `EQ-016` las declara tres dimensiones distintas: un menor puede tener la
-- autorización aprobada y no haber dado su asentimiento, y ese caso tiene que
-- poder representarse sin que ninguna de las dos lo tape.
--
-- Un disparador exige que la persona sea menor en el momento del acto: un adulto
-- no da asentimiento, da consentimiento. Una fila histórica de cuando sí era
-- menor se conserva y no vuelve a intervenir: la derivación de un adulto es
-- `no_requerido` (ver `dominio/modelo/menores.py`).
CREATE TABLE IF NOT EXISTS asentimiento_evento (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    version       text NOT NULL,
    alcance       text NOT NULL DEFAULT 'asentimiento' CHECK (alcance = 'asentimiento'),
    estado        text NOT NULL CHECK (estado IN ('otorgado', 'rechazado', 'revocado')),
    comprobante   text NOT NULL CHECK (comprobante ~ '^[0-9a-f]{64}$'),
    momento       timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT asentimiento_evento_version_asentimiento
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

COMMENT ON TABLE asentimiento_evento IS
    'Historial inmutable del asentimiento del menor (EQ-016). Dimension '
    'independiente del consentimiento y de la autorizacion del representante. '
    'Solo admite filas de una persona menor de edad.';

CREATE INDEX IF NOT EXISTS asentimiento_evento_por_sujeto
    ON asentimiento_evento (sujeto_google, momento DESC, id DESC);

-- ---------------------------------------------------------------------------
-- representante_evidencia · metadatos de cada intento de carga
-- ---------------------------------------------------------------------------
-- El PDF no está aquí. `EQ-021` lo pone en almacenamiento privado del equipo;
-- esta tabla guarda la referencia opaca y estable a ese archivo, su huella, su
-- tipo, su tamaño, cuándo llegó y qué versión del documento se firmó.
--
-- La versión es lo que la revisión echó en falta: sin ella una autorización
-- firmada sobre un texto viejo parecería cubrir uno nuevo. Con la clave foránea
-- compuesta, además, sólo puede apuntar a una versión de alcance
-- `representante`.
--
-- `referencia !~* '^https?://'` es la regla de `EQ-021` hecha restricción: un
-- enlace público o mutable del Drive personal del estudiante NO es evidencia
-- definitiva, y la base lo rechaza en vez de confiar en que nadie lo escriba.
--
-- `UNIQUE (sujeto_google, intento)` es lo que conserva el intento anterior
-- cuando llega uno nuevo: una carga nueva es una fila nueva con el número
-- siguiente, nunca un UPDATE de la anterior. La numeración es por persona y no
-- por versión, para que el historial de cargas se lea entero de una vez.
CREATE TABLE IF NOT EXISTS representante_evidencia (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    intento       integer NOT NULL CHECK (intento > 0),
    version       text NOT NULL,
    alcance       text NOT NULL DEFAULT 'representante' CHECK (alcance = 'representante'),
    referencia    text NOT NULL
                      CHECK (btrim(referencia) <> '' AND referencia !~* '^https?://'),
    sha256        text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    tipo_mime     text NOT NULL CHECK (tipo_mime = 'application/pdf'),
    tamano_bytes  integer NOT NULL CHECK (tamano_bytes > 0 AND tamano_bytes <= 10485760),
    recibido_en   timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT representante_evidencia_intento_unico UNIQUE (sujeto_google, intento),
    CONSTRAINT representante_evidencia_version_representante
        FOREIGN KEY (version, alcance)
        REFERENCES consentimiento_version (codigo, alcance) ON DELETE RESTRICT
);

COMMENT ON TABLE representante_evidencia IS
    'Metadatos de cada intento de carga de la autorizacion del representante '
    '(EQ-021), con la version exacta del documento firmado. El archivo vive '
    'fuera de PostgreSQL: aqui solo hay referencia opaca, huella, tipo, tamano '
    'y momento. Sin cedula, telefono ni correo del representante.';

CREATE INDEX IF NOT EXISTS representante_evidencia_por_sujeto
    ON representante_evidencia (sujeto_google, version, intento DESC);

-- ---------------------------------------------------------------------------
-- representante_revision · quién resolvió cada intento, y cuándo
-- ---------------------------------------------------------------------------
-- Tabla aparte y no dos columnas en `representante_evidencia`: `EQ-016` exige
-- que toda aprobación o rechazo cree un evento, y unas columnas en la fila del
-- intento habrían significado sobrescribir la revisión anterior.
--
-- El motivo es obligatorio cuando se rechaza —`EQ-021` pide un motivo
-- comprensible— y la base lo exige en vez de confiarlo al borde.
CREATE TABLE IF NOT EXISTS representante_revision (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evidencia    bigint NOT NULL REFERENCES representante_evidencia (id) ON DELETE RESTRICT,
    resultado    text NOT NULL CHECK (resultado IN ('aprobada', 'rechazada')),
    revisada_por text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    revisada_en  timestamp with time zone NOT NULL DEFAULT now(),
    motivo       text,
    CONSTRAINT representante_revision_motivo_al_rechazar
        CHECK (resultado <> 'rechazada' OR btrim(coalesce(motivo, '')) <> '')
);

COMMENT ON TABLE representante_revision IS
    'Cada aprobacion o rechazo de una evidencia, con actor y fecha (EQ-016). '
    'Solo se inserta: un disparador rechaza UPDATE y DELETE. La estructura '
    'admite varias por evidencia; la regla de la Fase 3 - sesion 2 solo admite '
    'una, y corregir se hace con una carga nueva.';

CREATE INDEX IF NOT EXISTS representante_revision_por_evidencia
    ON representante_revision (evidencia, revisada_en DESC, id DESC);

-- ---------------------------------------------------------------------------
-- rol_asignacion · el ÚNICO rol que EQ-023 crea y que hoy no existe
-- ---------------------------------------------------------------------------
-- ⚠️ Esto no es un segundo sistema de roles. Los dos roles que el sistema ya
-- resuelve —`estudiante` y `docente`— siguen decidiéndose exactamente donde se
-- deciden hoy: `RegistroDeDocentes` (lista manual del entorno) y
-- `solicitud_docente` (`10-solicitud-docente.sql`). Esta tabla no los contiene y
-- su CHECK no los admite, así que no puede haber dos respuestas para el mismo
-- rol.
--
-- Lo que sí falta hoy es `investigador_administrador` de `EQ-023`: no existe en
-- ningún almacén ni en ningún código, y sin él «un investigador autorizado
-- verifica la evidencia» no se puede comprobar. Esta tabla es ese hueco, y nada
-- más. `representante_revision.revisada_por` es su consumidor concreto en esta
-- misma sesión.
--
-- Nace vacía. Yeison y Fabian recibirán el rol por una operación explícita y
-- auditable, no por un correo escrito dentro del código o de una migración: el
-- encargo lo prohíbe y `EQ-023` habla de asignación, no de constante.
--
-- Retirar un rol es un acto auditable igual que concederlo: `revocado_por` y
-- `revocado_en` van juntos o no van, porque una revocación sin autor no explica
-- quién dejó de confiar ni cuándo. Esta tabla admite UPDATE —es como se revoca—
-- y por eso no lleva el disparador de inmutabilidad; lo que no admite es perder
-- la fila ni revocar en el anonimato.
CREATE TABLE IF NOT EXISTS rol_asignacion (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sujeto_google text NOT NULL REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    rol           text NOT NULL CHECK (rol IN ('investigador_administrador')),
    otorgado_por  text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    otorgado_en   timestamp with time zone NOT NULL DEFAULT now(),
    revocado_por  text REFERENCES persona (sujeto_google) ON DELETE RESTRICT,
    revocado_en   timestamp with time zone,
    CONSTRAINT rol_asignacion_revocacion_posterior
        CHECK (revocado_en IS NULL OR revocado_en >= otorgado_en),
    CONSTRAINT rol_asignacion_revocacion_auditada
        CHECK ((revocado_en IS NULL) = (revocado_por IS NULL))
);

COMMENT ON TABLE rol_asignacion IS
    'Asignacion persistente de investigador_administrador (EQ-023). No sustituye '
    'ni duplica el rol docente, que sigue en RegistroDeDocentes y '
    'solicitud_docente. Nace vacia: ningun correo se siembra aqui. Revocar '
    'registra quien y cuando, o la fila no se acepta.';

-- Una sola asignación vigente por persona y rol; las revocadas se conservan.
CREATE UNIQUE INDEX IF NOT EXISTS rol_asignacion_vigente
    ON rol_asignacion (sujeto_google, rol)
    WHERE revocado_en IS NULL;

-- ===========================================================================
-- GARANTIAS ACTIVAS · lo que un comentario no puede sostener
-- ===========================================================================
--
-- Los disparadores de aquí abajo existen porque la primera revisión devolvió
-- exactamente eso: reglas descritas en prosa y aplicadas sólo en Python. Un
-- INSERT o un UPDATE con SQL crudo las saltaba entero. Ahora las pruebas
-- negativas se escriben en SQL crudo, sin adaptador de por medio, y fallan
-- porque PostgreSQL las rechaza.
--
-- Ningún mensaje de estos disparadores nombra a una persona, un correo, una
-- referencia de archivo ni un código: un error de base acaba en una consola, en
-- un registro y en una captura pegada en un chat.

-- --- la version requerida · UNA sola redaccion de la regla ------------------
-- La clave foránea compuesta ya garantiza el ALCANCE. Lo que ninguna clave
-- foránea puede expresar es el TIEMPO.
--
-- ⚠️ **Corregido tras la segunda revisión (hito A2).** La versión anterior de
-- este archivo preguntaba «¿cuál es la más reciente ENTRE LAS VIGENTES?», y esa
-- pregunta tiene una respuesta equivocada en un caso real y reproducible:
--
--     v1 · empieza hace 30 días, sin fecha de vencimiento
--     v2 · empieza hace 20 días, venció hace 10
--
-- Con aquella regla ganaba `v1`, porque sigue abierta. Pero publicar `v2`
-- **desplazó a `v1` de forma definitiva**: que el texto viejo no llevara fecha
-- de caducidad no lo devuelve al presente, y aceptar términos retirados no
-- autoriza nada. El sistema tiene que quedarse sin versión requerida y decirlo.
--
-- La regla aprobada tiene dos pasos, y el orden es el contrato:
--
--   1. la versión requerida es la **más reciente que YA COMENZÓ**
--      (`vigente_desde <= now()`), con `vigente_desde DESC, codigo DESC` como
--      desempate determinista;
--   2. **sólo entonces** se evalúa si esa versión sigue vigente. Si venció y no
--      hay sucesora ya iniciada, no hay versión requerida.
--
-- Nunca se retrocede a una versión anterior, y una versión futura no desplaza a
-- la actual antes de su `vigente_desde` — no ha comenzado, así que el paso 1 no
-- la considera.
--
-- Es una función y no una consulta copiada porque la usan tres consumidores
-- —el disparador de abajo, `AdaptadorVersionesDeConsentimientoPostgres` y la
-- lectura del estado vigente— y tres redacciones de la misma regla acabarían
-- eligiendo versiones distintas. `STABLE` la hace utilizable dentro de una
-- consulta sin recalcularla por fila.
CREATE OR REPLACE FUNCTION didaxia_version_requerida(el_alcance text) RETURNS text
LANGUAGE sql STABLE AS $funcion$
    SELECT mas_reciente.codigo
      FROM (
          SELECT codigo, vigente_hasta
            FROM consentimiento_version
           WHERE alcance = el_alcance
             AND vigente_desde <= now()
           ORDER BY vigente_desde DESC, codigo DESC
           LIMIT 1
      ) AS mas_reciente
     WHERE mas_reciente.vigente_hasta IS NULL
        OR now() < mas_reciente.vigente_hasta;
$funcion$;

COMMENT ON FUNCTION didaxia_version_requerida(text) IS
    'La version que rige AHORA en un alcance, o NULL. Dos pasos: la mas '
    'reciente que ya comenzo, y solo despues si esa sigue vigente. Nunca '
    'retrocede a una anterior. Unica redaccion de la regla (hito A2).';

-- --- que version puede usar cada acto ---------------------------------------
-- Otorgar, rechazar y cargar evidencia tienen que usar **exactamente la versión
-- requerida** de su alcance. No basta con que una versión antigua siga
-- temporalmente abierta: si fue desplazada, aceptarla no autoriza el tratamiento
-- que hoy se hace.
--
-- **Revocar tiene otra semántica, y es deliberado.** Una revocación retira la
-- concesión que efectivamente se otorgó (`EQ-022`), así que:
--
--   - referencia la versión del último otorgamiento del historial;
--   - funciona aunque ese documento haya vencido o haya sido desplazado —quien
--     otorgó conserva el derecho a retirarlo—;
--   - **no** puede revocar una versión arbitraria que nunca se otorgó.
--
-- Y revocar no reabre nada: el acto siguiente vuelve a pasar por la rama de la
-- versión requerida, así que tras revocar `v1` no se puede reotorgar `v1`.
--
-- `TG_ARGV[0]` nombra la columna de momento de cada tabla —`momento` en los
-- eventos, `recibido_en` en la evidencia— para que la regla viva una sola vez.
-- `estado` se lee de `to_jsonb(NEW)` porque `representante_evidencia` no tiene
-- esa columna: allí devuelve NULL y el acto va por la rama normal.
CREATE OR REPLACE FUNCTION didaxia_version_del_acto() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    momento_del_acto timestamp with time zone;
    estado_del_acto  text;
    alcance_real     text;
    version_otorgada text;
    requerida        text;
BEGIN
    momento_del_acto := (to_jsonb(NEW) ->> TG_ARGV[0])::timestamp with time zone;
    estado_del_acto  := to_jsonb(NEW) ->> 'estado';

    IF momento_del_acto > now() THEN
        RAISE EXCEPTION 'un acto no se puede fechar en el futuro'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT alcance INTO alcance_real
      FROM consentimiento_version WHERE codigo = NEW.version;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la version referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    -- El alcance ya lo garantiza la clave foranea compuesta, pero este disparador
    -- corre ANTES de comprobarla y la enmascararia con otro motivo. Se rechaza
    -- aqui con el MISMO codigo de error, para que un cruce de alcance se lea
    -- siempre igual venga de donde venga.
    IF alcance_real <> NEW.alcance THEN
        RAISE EXCEPTION 'la version referenciada pertenece a otro alcance'
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF estado_del_acto = 'revocado' THEN
        -- La vigencia NO se comprueba: se retira lo concedido, no se acepta nada.
        EXECUTE format(
            'SELECT version FROM %I WHERE sujeto_google = $1 AND estado = ''otorgado'''
            || ' ORDER BY momento DESC, id DESC LIMIT 1', TG_TABLE_NAME)
          INTO version_otorgada USING NEW.sujeto_google;
        IF version_otorgada IS NULL OR version_otorgada <> NEW.version THEN
            RAISE EXCEPTION 'una revocacion solo retira la concesion efectivamente otorgada'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    requerida := didaxia_version_requerida(NEW.alcance);
    IF requerida IS NULL THEN
        RAISE EXCEPTION 'no hay version requerida vigente para este alcance'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.version <> requerida THEN
        RAISE EXCEPTION 'el acto tiene que usar la version requerida de su alcance'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_evento_version_del_acto
    BEFORE INSERT ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('momento');

CREATE OR REPLACE TRIGGER asentimiento_evento_version_del_acto
    BEFORE INSERT ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('momento');

CREATE OR REPLACE TRIGGER representante_evidencia_version_del_acto
    BEFORE INSERT ON representante_evidencia
    FOR EACH ROW EXECUTE FUNCTION didaxia_version_del_acto('recibido_en');

-- Los disparadores de la primera versión de este archivo se retiran por nombre.
-- `CREATE OR REPLACE TRIGGER` no los alcanza —el nombre cambió— y dejarlos vivos
-- aplicaría la regla vieja además de la nueva. `IF EXISTS` mantiene el archivo
-- repetible sobre una base que nunca los tuvo.
--
-- ⚠️ Es el único DROP de la migración 11 y no toca datos: retira dos objetos que
-- esta misma migración creó en su versión anterior, todavía sin integrar ni
-- aplicar a producción. Ninguna fila se ve afectada.
DROP TRIGGER IF EXISTS consentimiento_evento_version_vigente ON consentimiento_evento;
DROP TRIGGER IF EXISTS asentimiento_evento_version_vigente ON asentimiento_evento;
DROP TRIGGER IF EXISTS representante_evidencia_version_vigente ON representante_evidencia;
DROP FUNCTION IF EXISTS didaxia_version_vigente_en_el_acto();

-- --- categoría de edad -----------------------------------------------------
-- `EQ-016` hace depender el régimen entero de la edad, así que la categoría con
-- la que se emitió un consentimiento es parte del acto y no un dato de apoyo.
-- Se DERIVA aquí, con la fila de `persona` que la transacción ya tiene
-- bloqueada, y se sobrescribe lo que viniera en el INSERT: aceptar esa categoría
-- del borde habría dejado la regla de los 18 años en manos del cliente.
--
-- Sin edad declarada no hay régimen que aplicar y el consentimiento no se
-- registra. No se asume mayoría de edad: es la corrección deliberada de `DD-26`.
CREATE OR REPLACE FUNCTION didaxia_derivar_categoria_edad() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    edad integer;
BEGIN
    SELECT p.edad_declarada INTO edad
      FROM persona p WHERE p.sujeto_google = NEW.sujeto_google;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la persona referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF edad IS NULL THEN
        RAISE EXCEPTION 'no se registra consentimiento sin edad declarada'
            USING ERRCODE = 'check_violation';
    END IF;
    -- 18 es la mayoria de edad legal de RL-09 y EQ-016, no un umbral calibrable.
    -- `pruebas/unidad/test_dominio_consentimiento.py` comprueba que este literal
    -- y `dominio.modelo.identidad.MAYORIA_DE_EDAD` sigan diciendo lo mismo.
    NEW.categoria_edad := CASE WHEN edad < 18 THEN 'menor' ELSE 'adulto' END;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_evento_categoria_edad
    BEFORE INSERT ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_derivar_categoria_edad();

-- --- asentimiento sólo de menores ------------------------------------------
-- Un adulto no da asentimiento: da consentimiento. Sin esta barrera, una fila de
-- asentimiento rechazado podía bloquear a una persona mayor de edad a la que esa
-- dimensión ya no le corresponde.
CREATE OR REPLACE FUNCTION didaxia_exigir_persona_menor() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    edad integer;
BEGIN
    SELECT p.edad_declarada INTO edad
      FROM persona p WHERE p.sujeto_google = NEW.sujeto_google;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'la persona referenciada no existe'
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF edad IS NULL OR edad >= 18 THEN
        RAISE EXCEPTION 'el asentimiento solo corresponde a una persona menor de edad'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$funcion$;

CREATE OR REPLACE TRIGGER asentimiento_evento_solo_menores
    BEFORE INSERT ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_exigir_persona_menor();

-- --- finalidades obligatorias ----------------------------------------------
-- `EQ-021`: la aceptación cubre las seis finalidades obligatorias. Una versión
-- que declarara menos habilitaría el tutor autorizando menos de lo que el
-- sistema hace, que es la forma más silenciosa de incumplir.
--
-- Es un disparador de restricción DIFERIDO porque la versión y sus finalidades
-- se insertan en sentencias distintas de la misma transacción: comprobarlo al
-- insertar la versión rechazaría siempre. Diferido, se comprueba al confirmar.
--
-- Cuenta contra el catálogo entero, no contra una lista escrita aquí: añadir una
-- séptima finalidad en una migración futura hará que las versiones nuevas tengan
-- que cubrirla, y ese es el efecto deliberado de tocar el catálogo.
CREATE OR REPLACE FUNCTION didaxia_exigir_finalidades_obligatorias() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
DECLARE
    sin_cubrir integer;
BEGIN
    SELECT count(*) INTO sin_cubrir
      FROM consentimiento_finalidad f
     WHERE NOT EXISTS (
         SELECT 1 FROM consentimiento_version_finalidad vf
          WHERE vf.version = NEW.codigo AND vf.finalidad = f.codigo);
    IF sin_cubrir > 0 THEN
        RAISE EXCEPTION 'una version publicada tiene que cubrir todas las finalidades obligatorias'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$funcion$;

CREATE CONSTRAINT TRIGGER consentimiento_version_finalidades_obligatorias
    AFTER INSERT ON consentimiento_version
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION didaxia_exigir_finalidades_obligatorias();

-- --- inmutabilidad ---------------------------------------------------------
-- Un historial que se puede editar no es un historial. `EQ-016` y `EQ-022` hacen
-- que estas filas sean la prueba de qué se autorizó y cuándo; si la conexión de
-- la aplicación puede reescribirlas, esa prueba vale lo que valga la disciplina
-- de quien escriba la siguiente consulta.
--
-- ⚠️ Sin puerta trasera, y es deliberado. Esta función no mira ninguna variable
-- de sesión, ningún indicador ni ningún rol: no existe una forma de
-- «desactivarla desde la aplicación», porque un interruptor accesible al
-- adaptador normal habría sido exactamente el bypass que la revisión prohíbe.
-- Retirarla exige una operación de esquema —ser dueño de la tabla y desactivar
-- el disparador— que ningún adaptador de este árbol realiza.
--
-- La sesión 4 tendrá que construir el camino excepcional que `EQ-022` necesita
-- para una supresión procedente: explícito, separado del acceso ordinario y
-- auditado. No se diseña aquí y no se deja preparado a medias.
CREATE OR REPLACE FUNCTION didaxia_rechazar_modificacion() RETURNS trigger
LANGUAGE plpgsql AS $funcion$
BEGIN
    RAISE EXCEPTION 'fila inmutable: esta tabla no admite UPDATE ni DELETE'
        USING ERRCODE = 'check_violation',
              HINT = 'la supresion procedente de EQ-022 es un camino aparte de la sesion 4';
    RETURN NULL;
END;
$funcion$;

CREATE OR REPLACE TRIGGER consentimiento_version_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER consentimiento_version_finalidad_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_version_finalidad
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER consentimiento_evento_inmutable
    BEFORE UPDATE OR DELETE ON consentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER asentimiento_evento_inmutable
    BEFORE UPDATE OR DELETE ON asentimiento_evento
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER representante_evidencia_inmutable
    BEFORE UPDATE OR DELETE ON representante_evidencia
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();

CREATE OR REPLACE TRIGGER representante_revision_inmutable
    BEFORE UPDATE OR DELETE ON representante_revision
    FOR EACH ROW EXECUTE FUNCTION didaxia_rechazar_modificacion();
