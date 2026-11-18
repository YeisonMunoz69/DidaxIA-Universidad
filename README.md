# DidaxIA

**La versión oficial de DidaxIA está en funcionamiento.** La portada explica el proyecto y presenta sus espacios por rol. El tutor requiere acceso institucional.

- [Portada oficial de DidaxIA](https://didaxia.pro/)
- [Entrar a la plataforma](https://app.didaxia.pro/)

Este repositorio privado reúne el código, el corpus y las instrucciones de instalación de la entrega universitaria. [Ver la versión de entrega](https://github.com/YeisonMunoz69/DidaxIA-Universidad/tree/entrega-universitaria).

## El trabajo de grado

Comprender el cálculo diferencial exige vincular fórmulas, gráficas y argumentos. En grupos numerosos, resulta difícil orientar a cada estudiante justo cuando surge una duda. Para ampliar ese acompañamiento se desarrolló DidaxIA, un tutor conversacional en español que guía la resolución de límites y derivadas y registra indicios observables de dificultades cognitivas y afectivas.

La revisión sistemática, reportada según las directrices PRISMA, reunió 162 informes sobre factores del estudiante, inteligencia artificial generativa y didáctica del cálculo. La síntesis propuso catorce grupos didácticos y siete dimensiones de evaluación. Con la retroalimentación de dos docentes, los hallazgos se tradujeron en treinta requisitos verificables. En el prototipo, la revisión documental llevó a retirar resultados correctos, lo que motivó una comprobación independiente.

La arquitectura hexagonal (que conecta el núcleo pedagógico con servicios independientes) separó la generación de explicaciones, la búsqueda de fuentes curriculares y la comprobación de expresiones con SymPy (motor de cálculo simbólico). La plataforma conserva el ejercicio entre mensajes, formula preguntas, gradúa las pistas e integra gráficas interactivas. En una ejecución se registraron 8127 pruebas automatizadas aprobadas.

Durante un piloto formativo y voluntario de cuatro semanas en la Institución Universitaria Colegio Mayor del Cauca, 113 estudiantes aportaron 1473 pares completos de mensajes en 251 conversaciones. La satisfacción general fue favorable en 62 de 82 respuestas numéricas (75,6 por ciento). Ambas docentes asignaron 5 de 5 a los cuatro criterios de uso y coincidieron en valorar favorablemente 13 de los 26 criterios de contenido. El análisis identificó dos expresiones de tensión, dos fragmentos para revisión conceptual y cero reiteraciones del mismo error en cinco reintentos comparables.

La experiencia documentó la viabilidad del acompañamiento en aula y orientó ajustes del teclado matemático móvil. DidaxIA aporta información contextualizada para el seguimiento docente y una base para evaluar el aprendizaje mediante tareas independientes.

Los datos agregados del piloto, los ítems de los instrumentos y el verificador de cifras están disponibles en el [paquete de evidencia del estudio, versión 0.2.0](https://github.com/YeisonMunoz69/didaxia-research-artifacts/tree/v0.2.0). El paquete permite comprobar los recuentos y las distribuciones publicados y examinar un caso guionado de desarrollo. Los registros individuales se conservan bajo acceso restringido.

>  **Recorrido visual completo:** Para explorar en detalle las capturas reales de la plataforma organizadas por rol (**Estudiante**, **Docente**, **Investigador**) en computador y dispositivos móviles Android, consulta la sección [Recorrido visual del sistema: roles, pantallas y funcionalidades](#recorrido-visual-del-sistema-roles-pantallas-y-funcionalidades) al final de este documento.

## Instalación de la entrega universitaria

La instalación usa Svelte para la interfaz, FastAPI para la API, PostgreSQL con pgvector para los datos y el índice, y Caddy para servir la aplicación y la portada. El archivo `VERSION-ENTREGA.txt` identifica el corte técnico descrito en la monografía y la huella del manifiesto del corpus. El catálogo de la biblioteca guarda [los permisos por obra](contenido/corpus/fuentes.json) y [la correspondencia de páginas](contenido/corpus/partes.json).

## 1. Preparar el entorno

Use Docker Desktop con contenedores Linux o una VPS Linux de 64 bits con Docker Engine. En ambos entornos se requiere Docker Compose 2.24.4 o posterior, `curl`, `jq`, `openssl` y las herramientas de extracción y verificación del sistema. Como punto de partida reserve 4 GB de RAM y 20 GB de disco libres; 8 GB de RAM dan margen para construir y cargar el modelo. La primera instalación descarga imágenes, dependencias y el codificador multilingüe E5 (modelo que convierte textos en vectores para buscar pasajes relacionados). Permita esas descargas y la salida hacia los servicios de identidad y generación que autorice la Universidad. La [guía de Docker para Ubuntu](https://docs.docker.com/engine/install/ubuntu/) explica cómo instalar el motor y el complemento de Compose.

Clone el repositorio institucional o descomprima el paquete en una carpeta privada. Ejecute estos comandos desde la raíz de la copia. En Windows, use Git Bash y Docker Desktop en modo de contenedores Linux.

```bash
cat VERSION-ENTREGA.txt
sha256sum -c MANIFIESTO-CORPUS.sha256
docker compose version
umask 077
test -e .env || cp .env.ejemplo .env
chmod 600 .env
openssl rand -hex 32
```

El último comando genera una contraseña nueva. Escríbala en `PGPASSWORD_AGENTE` y en la parte de contraseña de `AGENTE_BD`. Si se usa una contraseña hexadecimal, no hay que codificar caracteres especiales en la dirección de conexión. El archivo `.env` permanece en el servidor y se administra por el canal de secretos de la Universidad.

## 2. Elegir Docker local o VPS

En **Docker local**, configure en `.env` la contraseña de PostgreSQL, la clave del proveedor, el cliente web de Google, el dominio institucional y las cuentas propietarias. Puede dejar los ejemplos de DNS y HTTPS tal como están en la plantilla. El perfil local los sustituye por `http://localhost:18080` para la aplicación y `http://localhost:18081` para la portada. Ambos puertos quedan disponibles únicamente en el equipo donde corre Docker. Si hay un conflicto, cambie `DIDAXIA_PUERTO_APP_LOCAL` o `DIDAXIA_PUERTO_PORTADA_LOCAL` antes de construir.

Registre `http://localhost` y `http://localhost:18080` como orígenes autorizados del [cliente web de Google](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid). Ajuste el segundo al puerto de la aplicación si lo cambió. Abra el tutor con `localhost` y use una cuenta institucional autorizada. El botón de Google y el proveedor de generación requieren sus servicios respectivos, también al ejecutar Docker en el equipo.

En una **VPS**, configure las direcciones HTTPS y el acceso institucional que se describen a continuación.

## 3. Configurar dominio, acceso y proveedor

Para una instalación en servidor, configure tres nombres DNS: aplicación, portada y alias de la portada. Los tres deben llegar a la VPS. Abra los puertos 80 y 443 para Caddy; PostgreSQL y la API interna quedan en la red de Compose. Use en Google un [cliente OAuth web](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid) con el origen HTTPS exacto de la aplicación entre los orígenes autorizados. La cuenta de prueba debe pertenecer al dominio institucional de Google Workspace configurado en `DOMINIO_INSTITUCIONAL`. El rol propietario se asigna a las cuentas enumeradas en `INVESTIGADORES_PROPIETARIOS` al iniciar sesión.

Ejemplo de valores para editar en `.env`. Reemplace los nombres, cuentas y marcadores por los de su instalación:

```dotenv
PGPASSWORD_AGENTE=CLAVE_HEXADECIMAL_GENERADA
AGENTE_BD=postgresql://agente:CLAVE_HEXADECIMAL_GENERADA@base:5432/agente
AGENTE_LLM=deepseek
DEEPSEEK_API_KEY=CLAVE_PROPIA_AUTORIZADA
GOOGLE_CLIENT_ID=CLIENTE_WEB_PROPIO.apps.googleusercontent.com
DOMINIO_INSTITUCIONAL=universidad.example
INVESTIGADORES_PROPIETARIOS=operador@universidad.example
DOCENTES_AUTORIZADOS=
INVESTIGADORES_AUTORIZADOS=
DOMINIO=app.didaxia.universidad.example
DOMINIO_PUBLICO=didaxia.universidad.example
DIDAXIA_DOMINIO_ALIAS=www.didaxia.universidad.example
ORIGEN_APLICACION=https://app.didaxia.universidad.example
ORIGEN_PUBLICO=https://didaxia.universidad.example
DIDAXIA_IP_PUBLICACION=0.0.0.0
DIDAXIA_PUERTO_HTTP=80
DIDAXIA_PUERTO_HTTPS=443
DIDAXIA_PILOTO_UNIVERSIDAD=0
CORREO_INVESTIGACION=didaxia@universidad.example
CORREO_PRIVACIDAD=privacidad@universidad.example
RESEND_API_KEY=
RESEND_REMITENTE=
```

Use una clave del proveedor de generación autorizada para esta instalación. Las solicitudes del tutor pueden incluir pasajes recuperados; confirme que el proveedor y su tratamiento de datos estén autorizados para el material de la Universidad. Para habilitar avisos por correo configure juntos `RESEND_API_KEY` y `RESEND_REMITENTE`, con un remitente verificado. Con ambos valores vacíos los avisos quedan sin envío externo. Configure buzones institucionales atendidos para investigación y privacidad. El modo piloto queda desactivado en el perfil universitario.

Si la VPS ya cuenta con un proxy inverso institucional (servidor que recibe las conexiones HTTPS y las pasa a la aplicación), elija el perfil de VPS compartida. Defina `DIDAXIA_DOMINIO_APP`, `DIDAXIA_DOMINIO_PUBLICO` y `DIDAXIA_DOMINIO_ALIAS` con los nombres DNS respectivos, y `DIDAXIA_PUERTO_HTTP` con el puerto asignado. El proxy termina HTTPS, conserva el encabezado `Host` y reenvía al puerto de bucle local que publica Compose. Mantenga `ORIGEN_APLICACION` y `ORIGEN_PUBLICO` como las direcciones HTTPS que usa el navegador. Revise `frontend/publico/robots.txt` si la Universidad decide indexar su portada. Para una entrega de acceso restringido, la Universidad controla el acceso en el borde; `robots.txt` no controla quién puede entrar.

## 4. Aplicar migraciones, cargar el corpus y arrancar

Abra una sesión de Bash sin variables exportadas de otra instalación de DidaxIA. Docker Compose da prioridad a esas variables sobre las del archivo de configuración. Defina una función para esta sesión de Bash según el entorno. Ejecute solo el bloque que corresponda y use la misma función en los pasos siguientes.

```bash
# Docker local
dc() { docker compose --env-file .env -f compose.produccion.yaml -f compose.universidad.yaml -f compose.local.yaml "$@"; }
```

```bash
# VPS dedicada
dc() { docker compose --env-file .env -f compose.produccion.yaml -f compose.universidad.yaml "$@"; }
```

```bash
# VPS compartida
dc() { docker compose --env-file .env -f compose.produccion.yaml -f compose.universidad.yaml -f compose.vps-compartida.yaml "$@"; }
```

En los tres entornos, ejecute:

```bash
dc config --quiet
dc up -d --build --wait --wait-timeout 2400
dc ps -a
```

Compose espera a PostgreSQL, ejecuta las migraciones versionadas en `infraestructura/esquema/` y carga los fragmentos admisibles de `contenido/corpus/fragmentos/` con el catálogo `fuentes.json`. El índice se guarda en PostgreSQL; no se distribuye una base precargada. Si la ingesta falla, se bloquea el inicio del backend. Después se sirve el frontend por Caddy. `migraciones`, `ingesta` y `frontend-build` deben quedar en estado `Exited (0)`; son trabajos de una sola pasada.

```bash
dc logs --tail=80 migraciones ingesta
dc logs --tail=80 backend caddy
```

El paquete conserva las obras, las transcripciones, las secciones en PDF y el catálogo de partes para que la biblioteca pueda abrir los materiales autorizados. La ingesta no extrae de nuevo los PDF: usa los fragmentos incluidos y excluye los que no cumplen la marca de revisión matemática. Los conceptos, el grafo y las plantillas del tutor se montan desde `contenido/` en modo de solo lectura.

Una base nueva no incluye consentimientos publicados. Antes de habilitar el uso con estudiantes, siga el procedimiento de publicación de este README con los textos aprobados por la Universidad. Consulte el estado antes de publicar. La instalación técnica puede verificarse con una cuenta propietaria de prueba sin copiar datos del piloto.

## 5. Verificar el recorrido

```bash
# Docker local. En VPS use las direcciones HTTPS de su instalación.
APP=http://localhost:18080
PUBLICO=http://localhost:18081
curl -fsS "$APP/api/salud" | jq '{faltantes, notificacion}'
curl -sS -o /dev/null -w '%{http_code}\n' "$APP/api/sesion"       # 401 sin sesión
curl -sS -o /dev/null -w '%{http_code}\n' "$PUBLICO/api/salud"    # 404
```

En una VPS, consulte también la ruta /robots.txt en el alias y compruebe que devuelve 301 hacia la portada. En una instalación con avisos habilitados, la respuesta debe traer `faltantes: []`. Si la Universidad aún no ha activado el correo, el sistema registra los avisos sin enviarlos y salud informa esa carencia. Cualquier otra entrada debe investigarse antes de habilitar el uso. El estado saludable de Compose solo confirma que la ruta responde.

Abra la aplicación e inicie sesión con la cuenta institucional de prueba. Compruebe que la interfaz identifica el rol esperado y que la consulta `GET /api/sesion` devuelve 200 después de entrar. En una conversación nueva escriba: «¿Cómo se obtiene la derivada de $x^2$ mediante el límite del cociente incremental?». Abra la fuente de la respuesta y compruebe que su identificador aparece entre los fragmentos del manifiesto y que la ficha corresponde a la obra y al pasaje citados. Si el turno no muestra fuente, registre el resultado como una prueba incompleta, incluso si la API está saludable. Guarde el commit, la huella del manifiesto, la fecha, la configuración sin valores secretos y los códigos de respuesta; omita tokens, correos de prueba y cookies.

## 6. Recuperar o actualizar

Antes de una actualización, guarde una copia del paquete anterior, anote el commit y respalde PostgreSQL, la custodia privada y las fotos de perfil según la política institucional. Por ejemplo, en la instalación que se está respaldando:

```bash
umask 077
mkdir -p "$HOME/respaldos-didaxia"
DUMP="$HOME/respaldos-didaxia/agente-$(date -u +%Y%m%dT%H%M%SZ).dump"
dc exec -T base pg_dump -U agente -d agente -Fc > "$DUMP" &&
  test -s "$DUMP" &&
  dc exec -T base pg_restore --list < "$DUMP" > /dev/null
```

Conserve el `.env` por el canal de custodia, los respaldos fuera del árbol y los volúmenes del proyecto. El archivo anterior comprueba que el volcado puede listarse; para comprobar que se puede restaurar, haga un ensayo en una instancia aislada. Si falla un servicio de arranque, revise los registros, corrija la causa y repita `dc up`. Si falla una actualización, vuelva al paquete de código anterior solo después de comprobar que el esquema sigue siendo compatible. Para revertir una migración incompatible, restaure un respaldo en una base aislada y verifíquelo antes de considerar el cambio en la instancia activa. Evite `down -v`, que elimina los volúmenes. Un reinicio del backend exige iniciar sesión de nuevo.

## 7. Publicar los textos de consentimiento

Use la función `dc` del perfil de VPS y una carpeta absoluta bajo custodia,
fuera de la entrega. El proceso del contenedor necesita permiso de lectura
sobre esa carpeta y sus archivos. Verifique que `dc ps` muestra la instancia
universitaria antes de continuar. Para revisar el paquete sin escritura:

```bash
PAQUETE=/ruta/privada/al/paquete-aprobado
dc run --rm --no-deps -T -v "$PAQUETE:/textos:ro" migraciones \
  python -m infraestructura.operacion.publicar_consentimiento \
  --manifiesto /textos/manifiesto.json --textos /textos --dry-run
```

Compare las huellas con la aprobación institucional. Solo después, en esa
misma instalación, consulte el estado y publique si corresponde. La dirección
de la base se toma dentro del contenedor, sin mostrar su contraseña:

```bash
dc run --rm --no-deps -T -v "$PAQUETE:/textos:ro" migraciones sh -ec '
  export AGENTE_BD_PUBLICACION="$AGENTE_BD"
  exec python -m infraestructura.operacion.estado_consentimiento \
    --manifiesto /textos/manifiesto.json --textos /textos'
dc run --rm --no-deps -T -v "$PAQUETE:/textos:ro" migraciones sh -ec '
  export AGENTE_BD_PUBLICACION="$AGENTE_BD" AGENTE_PUBLICACION_AUTORIZADA=1
  exec python -m infraestructura.operacion.publicar_consentimiento \
    --manifiesto /textos/manifiesto.json --textos /textos --confirmar-publicacion'
```

---

## Recorrido visual del sistema: roles, pantallas y funcionalidades

DidaxIA ofrece una experiencia diseñada para computadores de escritorio y dispositivos móviles (Android), adaptando sus vistas, controles y niveles de acceso según el rol de la persona usuaria: **Estudiante**, **Docente** o **Investigador / Administrador**.

A continuación se presenta un recorrido detallado por las capturas reales de la plataforma en funcionamiento, describiendo las funcionalidades que ofrece cada pantalla.

---

### 1. Espacio del Estudiante

El estudiante cuenta con un entorno integral para el aprendizaje del cálculo diferencial que combina diálogo socrático guiado, digitación matemática táctil, visualización gráfica interactiva, biblioteca digital universitaria y herramientas de control sobre su privacidad.

#### 1.1 Diálogo socrático y formulación matemática (PC y Android)

* **En computador de escritorio:**  
  El espacio de trabajo central reúne en una sola vista el historial de conversaciones previas (columna izquierda), el diálogo con el tutor socrático (panel central) y las referencias documentales asociadas (panel lateral derecho). El tutor orienta mediante preguntas reflexivas y pistas progresivas para que el estudiante construya su propio procedimiento, sin entregar la respuesta resuelta de manera automática. Todas las expresiones matemáticas se representan con alta fidelidad tipográfica mediante KaTeX, y el distintivo **«Verificado simbólicamente»** certifica que las operaciones algebraicas fueron contrastadas de forma determinista mediante el motor matemático SymPy, garantizando la exactitud del cálculo sin alucinaciones.

  [![Espacio de trabajo del estudiante en computador](OE3/var-conversacion-computador-claro-electrico.png)](OE3/var-conversacion-computador-claro-electrico.png)

* **En dispositivo móvil (Android): Flujo de consulta y exploración gráfica**  
  En pantallas compactas, la interfaz distribuye los controles de forma táctil para mantener siempre a la vista el hilo de la consulta, permitiendo pasar de la redacción matemática a la inspección gráfica interactiva:

  | 1. Redacción matemática táctil | 2. Solicitud de gráfica en el hilo | 3. Exploración visual de la curva |
  | :---: | :---: | :---: |
  | [![Escritura con teclado matemático en móvil](OE3/var-pregunta-telefono-claro-electrico.png)](OE3/var-pregunta-telefono-claro-electrico.png) | [![Solicitud de gráfica en el hilo conversacional](OE3/var-pregunta-telefono-claro-electrico-2.png)](OE3/var-pregunta-telefono-claro-electrico-2.png) | [![Visualización gráfica ampliada en móvil](OE3/var-pregunta-telefono-claro-electrico-3.png)](OE3/var-pregunta-telefono-claro-electrico-3.png) |
  | **Teclado matemático (MathLive):** Permite escribir fórmulas complejas (exponentes, fracciones, raíces y derivadas) dentro de una pregunta en lenguaje natural. | **Generación contextual:** El estudiante solicita la representación gráfica de la función en estudio directamente dentro del diálogo. | **Exploración táctil:** La curva se despliega con controles táctiles de acercamiento y desplazamiento para analizar su comportamiento y puntos clave. |

---

#### 1.2 Graficadora matemática interactiva (PC y Android)

Para apoyar la intuición geométrica, DidaxIA integra una graficadora matemática dinámica basada en JSXGraph que vincula la expresión analítica, la tabla de valores numéricos y la curva en el plano cartesiano.

* **En computador:**  
  Vista de pantalla completa donde la fórmula analítica y el plano cartesiano coexisten en el mismo campo visual, facilitando el análisis de curvas continuas, asíntotas y puntos coordenados.

  [![Graficadora interactiva en computador](OE3/var-grafica-computador-claro-electrico.png)](OE3/var-grafica-computador-claro-electrico.png)

* **En dispositivo móvil (Android):**  
  La graficadora móvil organiza la interacción en tres pestañas que permiten preparar, examinar y conservar las representaciones del ejercicio:

  | Funciones | Tabla de valores | Ajustes y exportación |
  | :---: | :---: | :---: |
  | [![Pestaña de funciones en celular](OE3/Cal-2.png)](OE3/Cal-2.png) | [![Pestaña de tabla de valores en celular](OE3/Cal-1.png)](OE3/Cal-1.png) | [![Pestaña de ajustes y exportación en celular](OE3/Cal-3.png)](OE3/Cal-3.png) |
  | **Entrada de fórmulas:** Selección y trazado de funciones analíticas en el plano. | **Evaluación numérica:** Ingreso de valores en la variable independiente para calcular al instante su correspondencia sobre la curva. | **Configuración:** Ajustes de cuadrícula, ejes y exportación de la gráfica en imagen para respaldar tareas o apuntes. |

---

#### 1.3 Biblioteca digital de cálculo y consulta de fuentes (PC y Android)

La plataforma integra las obras de referencia del curso universitario de cálculo, permitiendo a los estudiantes fundamentar su aprendizaje en fuentes bibliográficas oficiales.

* **En computador:**

  | Catálogo general de la biblioteca | Visor de lectura enfocada (Modo oscuro) |
  | :---: | :---: |
  | [![Catálogo general de la biblioteca en PC](OE3/var-biblioteca-computador-claro-electrico.png)](OE3/var-biblioteca-computador-claro-electrico.png) | [![Lectura enfocada en modo oscuro en PC](OE3/var-biblioteca-computador-oscuro-electrico.png)](OE3/var-biblioteca-computador-oscuro-electrico.png) |
  | **Catálogo de obras:** Colección indexada de libros de texto de cálculo organizados por unidades temáticas y capítulos. | **Lectura libre de distracciones:** Transcripción adaptada con fórmulas tipográficas, navegación entre secciones vecinas y enlace de retorno al ejercicio. |

* **En dispositivo móvil (Android):**

  | Índice táctil de secciones | Visor del documento editorial original |
  | :---: | :---: |
  | [![Índice de capítulos en móvil](OE3/Recursos-celular-1.png)](OE3/Recursos-celular-1.png) | [![Consulta del facsímil editorial en móvil](OE3/Recursos-celular-2.png)](OE3/Recursos-celular-2.png) |
  | **Navegación ágil:** Lista interactiva para localizar rápidamente capítulos, teoremas y ejercicios desde el teléfono. | **Facsímil en PDF:** Consulta directa de la página original del libro con su diagramación editorial, figuras y notas al pie. |

---

#### 1.4 Talleres interactivos y centro de recursos (PC y Android)

* **Visor de talleres guiados (PC):**  
  Permite a los estudiantes recorrer actividades estructuradas diapositiva a diapositiva (como talleres de derivación o límites), conectando cada consigna teórica o práctica con el apoyo conversacional del tutor sin perder el avance de la sesión.

  [![Visor de talleres en computador](OE3/var-diapositivas-computador-claro-electrico.png)](OE3/var-diapositivas-computador-claro-electrico.png)

* **Centro de recursos y notificaciones del curso (Android):**  
  Panel emergente accesible desde la cabecera móvil que mantiene al estudiante informado sobre cuestionarios o encuestas pendientes por responder, presentaciones compartidas por sus docentes y el estado de su autorización de acceso.

  | Centro de notificaciones y recursos del curso (Android) |
  | :---: |
  | [![Centro de notificaciones y recursos del curso en móvil](OE3/Notificaciones-estudiante.png)](OE3/Notificaciones-estudiante.png) |
  | **Avisos y recursos activos:** Acceso directo a encuestas formativas y presentaciones de clase, con apertura en pestaña independiente para no interrumpir el trabajo en curso. |

---

#### 1.5 Accesibilidad visual y privacidad del estudiante (PC y Android)

* **Personalización visual y contraste accesible (Android):**  
  Diseñado bajo pautas de accesibilidad web (WCAG AA), el sistema permite a cada estudiante configurar la apariencia para una lectura cómoda y descansada:

  | Ajustes de tema y tamaño tipográfico | Paletas de color accesibles |
  | :---: | :---: |
  | [![Ajustes de tema y tamaño de lectura](OE3/colores-1.png)](OE3/colores-1.png) | [![Selección de paletas de color de alto contraste](OE3/Colores-2.png)](OE3/Colores-2.png) |
  | **Preferencia de lectura:** Alternancia entre modo claro y oscuro, ajuste del tamaño de letra y control de animaciones. | **Combinaciones cromáticas:** Paletas como Azul eléctrico, Jade o Ámbar, diseñadas con relaciones de contraste óptimas para cualquier iluminación. |

* **Panel de privacidad y supresión voluntaria de cuenta (PC):**  
  DidaxIA promueve el respeto a la privacidad y los derechos de los usuarios. Desde este panel, el estudiante puede solicitar una copia descargable de sus registros o gestionar la eliminación voluntaria de su cuenta, contando con reautenticación institucional mediante Google y un período de gracia de 24 horas para revocar la solicitud si así lo decide.

  [![Panel de privacidad y supresión voluntaria de cuenta](OE3/eliminar-cuenta-voluntariamente.png)](OE3/eliminar-cuenta-voluntariamente.png)

---

### 2. Espacio del Docente

El docente dispone de un conjunto de herramientas para coordinar el trabajo de sus asignaturas, monitorear la participación formativa de su grupo y participar de forma activa en la supervisión de las respuestas generadas por la plataforma.

#### 2.1 Gestión de aulas y matrículas (PC y Android)

* **En dispositivo móvil y computador:**  
  Permite al docente gestionar sus asignaturas tanto desde el teléfono celular dentro del aula de clases como desde su equipo de cómputo:

  | Gestión móvil de clases (Android) | Directorio formal de estudiantes (PC) |
  | :---: | :---: |
  | [![Gestión de clases en celular](OE3/var-docenteclases-telefono-claro-electrico.png)](OE3/var-docenteclases-telefono-claro-electrico.png) | [![Directorio de estudiantes matriculados en la clase](OE3/directorio-estudiantes-docente.png)](OE3/directorio-estudiantes-docente.png) |
  | **Panel móvil de clase:** Visualización del código de inscripción para compartir con los alumnos, lista de inscritos y pestaña de solicitudes pendientes para autorizar ingresos con un solo toque. | **Directorio institucional de clase:** Vista detallada de los alumnos matriculados con nombre, correo institucional, estado de vinculación y enlace a su ficha individual. |

---

#### 2.2 Seguimiento pedagógico y analítica del grupo (PC)

Panel analítico que consolida la actividad del curso por períodos seleccionados. Permite al profesor identificar el grado de participación de los estudiantes, los momentos de mayor interacción con el tutor y la frecuencia de uso de los materiales de apoyo, facilitando la planeación de refuerzos temáticos en las sesiones presenciales.

[![Panel de seguimiento docente en computador](OE3/var-docente-computador-claro-electrico.png)](OE3/var-docente-computador-claro-electrico.png)

---

#### 2.3 Supervisión humana en el bucle y rectificación docente (PC)

Como mecanismo de aseguramiento de calidad académica (*Human-in-the-Loop*), el sistema cuenta con una cola de supervisión pedagógica. Cuando una respuesta del tutor carece de material bibliográfico asociado o amerita validación docente (por ejemplo, en límites trigonométricos especiales), el intercambio se somete a revisión:

[![Revisión y rectificación docente de una respuesta del tutor](OE3/docente-rectifica-respuesta.png)](OE3/docente-rectifica-respuesta.png)

* **Opciones de intervención:** El docente puede **aprobar** la explicación generada, **editarla** para enriquecerla con sus propias observaciones pedagógicas, o **rechazarla y redactar una corrección**.
* **Trazabilidad completa:** El sistema almacena tanto la propuesta inicial como la decisión final del profesor, manteniendo un registro transparente de la intervención.

---

### 3. Espacio del Investigador y Administración

El rol de investigador y administración institucional permite supervisar la operación del sistema a nivel global, diseñar y distribuir actividades académicas, y realizar auditorías cualitativas profundas bajo estrictas consideraciones éticas.

#### 3.1 Exploración matemática profesional (PC)

Los docentes e investigadores tienen acceso al modo Tutor profesional para experimentar con el diálogo conversacional y utilizar una graficadora avanzada capaz de comparar simultáneamente múltiples funciones matemáticas. Todas las consultas efectuadas en este espacio quedan catalogadas como uso profesional, aisladas de los registros de actividad de los estudiantes.

[![Graficadora en el espacio profesional del investigador](OE3/Graficas-docentes-investigadores.png)](OE3/Graficas-docentes-investigadores.png)

---

#### 3.2 Analítica institucional macro y trazabilidad documental (PC)

* **Filtros de analítica institucional:**  
  Permite acotar el análisis global de la plataforma por facultad, programa académico, período semestral o asignatura, identificando la población elegible y las condiciones de la consulta institucional.

  [![Filtros de analítica institucional en computador](OE3/var-investigador-computador-claro-electrico.png)](OE3/var-investigador-computador-claro-electrico.png)

* **Tablero de recuperación documental:**  
  Evalúa la disponibilidad de pasajes de los libros de cálculo en las respuestas del tutor, el nivel de apertura de fuentes por parte de los estudiantes y las obras más consultadas de la biblioteca.

  [![Detalle de indicadores de recuperación documental](OE3/var-investigadorcomputador-claro-electrico.png)](OE3/var-investigadorcomputador-claro-electrico.png)

---

#### 3.3 Gestión de equipo institucional y comunicaciones (PC)

* **Invitaciones seguras por rol:**  
  Generación y confirmación de enlaces únicos de invitación para vincular a nuevos docentes o investigadores, garantizando un gobierno seguro de roles y privilegios de acceso.

  [![Confirmación de invitación a cuenta docente](OE3/equipo-invitacion.png)](OE3/equipo-invitacion.png)

* **Compositor de correos institucionales:**  
  Herramienta de comunicación masiva con previsualización simultánea adaptable a pantallas de escritorio y teléfonos móviles, selección de destinatarios por clase o rol, y auditoría de envíos.

  [![Compositor de correo institucional con vista previa](OE3/Enviar-Correos.png)](OE3/Enviar-Correos.png)

---

#### 3.4 Creación y publicación de materiales pedagógicos (PC)

Facilita la autoría y programación de instrumentos formativos alineados con los objetivos de aprendizaje:

| Gestor de encuestas | Gestor de presentaciones y talleres |
| :---: | :---: |
| [![Gestor de encuestas del investigador](OE3/Captura-GestorDeEncuestas.png)](OE3/Captura-GestorDeEncuestas.png) | [![Biblioteca de presentaciones del investigador](OE3/Captura-GestorDePresentaciones.png)](OE3/Captura-GestorDePresentaciones.png) |
| **Encuestas formativas:** Creación, importación y seguimiento de cuestionarios dirigidos a grupos o docentes específicos. | **Biblioteca de actividades:** Control del ciclo de vida de los materiales (borradores, publicados y cerrados) con seguimiento de asignaciones. |

* **Editor interactivo de diapositivas de cálculo:**  
  Entorno de diseño instruccional para estructurar talleres secuenciales, incorporar retos de predicción matemática antes de graficar y vincular consignas con el tutor conversacional.

  [![Editor de una presentación de cálculo con navegación y propiedades](OE3/Captura-EditorDePresentaciones.png)](OE3/Captura-EditorDePresentaciones.png)

---

#### 3.5 Directorio global y fichas de seguimiento (PC)

* **Directorio institucional con protección de identidad:**  
  Listado global de participantes que incluye la posibilidad de enmascarar identificadores personales para revisiones analíticas seguras.

  [![Directorio de estudiantes con identificadores ocultos](OE3/Estudiantes-listado.png)](OE3/Estudiantes-listado.png)

* **Ficha individual de actividad:**  
  Resumen consolidado de la participación de un estudiante que muestra el recuento de turnos conversacionales, sesiones realizadas y días activos, facilitando el acceso a su trayectoria con fines de acompañamiento.

  [![Ficha detallada de actividad del estudiante](OE3/ficha-detallada-estudiante.png)](OE3/ficha-detallada-estudiante.png)

---

#### 3.6 Auditoría cualitativa e inspección profunda de conversaciones (PC)

Módulo especializado de auditoría pedagógica y técnica que permite examinar turnos reales del tutor en su contexto original para contrastar la efectividad del andamiaje formativo:

[![Inspección de conversación y auditoría en el espacio del investigador](OE3/Captura-conversacion-estudiante.png)](OE3/Captura-conversacion-estudiante.png)

1. **Anonimización inmediata:** La casilla *«Preparar captura sin identificadores visibles»* oculta nombres y correos institucionales para obtener evidencias seguras y éticas destinadas a la investigación académica.
2. **Nivel de andamiaje pedagógico registrado:** Señala de forma transparente la estrategia socrática asignada al turno (por ejemplo, *«Nivel 2 · te nombro la regla que aplica»*), permitiendo auditar la gradualidad de la ayuda antes de resolver el ejercicio.
3. **Comprobación matemática simbólica:** El distintivo *«Verificado simbólicamente»* certifica que la expresión matemática obtenida (como $\frac{d}{dx}(x^2-1)=2x$) superó la validación determinista de SymPy.
4. **Procedencia documental transparente:** El desplegable de fuentes permite abrir los pasajes bibliográficos exactos recuperados de los libros de cálculo para fundamentar la respuesta, permitiendo contrastar el texto original con la explicación generada.

