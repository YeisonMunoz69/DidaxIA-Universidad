# DidaxIA

**La versión oficial de DidaxIA está en funcionamiento.** La portada explica el proyecto y presenta sus espacios por rol. El tutor requiere acceso institucional.

- [Portada oficial de DidaxIA](https://didaxia.pro/)
- [Entrar a la plataforma](https://app.didaxia.pro/)

Este repositorio privado reúne el código, el corpus y las instrucciones de instalación de la entrega universitaria. [Ver la versión de entrega](https://github.com/YeisonMunoz69/DidaxIA-Universidad/tree/entrega-universitaria).

## El trabajo de grado

DidaxIA es un tutor conversacional en español para cálculo diferencial universitario. Ayuda a interpretar el ejercicio, revisar un intento y decidir cuánta ayuda ofrecer. Puede recuperar fragmentos de sus materiales y comprobar expresiones matemáticas con un motor simbólico (software que opera sobre fórmulas). La monografía describe cómo una revisión sistemática de 162 informes y la consulta a docentes orientaron 30 requisitos, y cómo estos se trasladaron a la arquitectura y a la implementación.

El equipo realizó un piloto formativo de cuatro semanas en la Institución Universitaria Colegio Mayor del Cauca. Se analizaron 1.473 pares completos de mensajes de 113 participantes. El piloto documentó el funcionamiento del tutor, dificultades para escribir consultas y las condiciones en que aparecieron indicios en el diálogo. La interpretación de esos indicios requiere una valoración independiente y el efecto sobre el aprendizaje queda por evaluar.

## La plataforma en computador y celular

Las capturas muestran cuentas, conversaciones y cifras de demostración. Los marcos conservan la pantalla completa en cada dispositivo.

| En computador | En celular |
| --- | --- |
| [![Tutor de DidaxIA en un computador, tema claro azul eléctrico](imagenes/tutor-computador.webp)](imagenes/tutor-computador.webp) | [![Teclado matemático en un celular, tema oscuro jade](imagenes/teclado-celular.webp)](imagenes/teclado-celular.webp) |
| **Tutor · Azul eléctrico.** El estudiante escribe una función, recibe una explicación y puede distinguir el resultado de la comprobación simbólica. | **Teclado matemático · Jade oscuro.** Permite introducir derivadas, límites y expresiones durante la consulta. |
| [![Panel docente de DidaxIA en un computador, tema claro ámbar](imagenes/docente-computador.webp)](imagenes/docente-computador.webp) | [![Recursos de investigación en un celular, tema claro azul eléctrico](imagenes/recursos-celular.webp)](imagenes/recursos-celular.webp) |
| **Panel docente · Ámbar.** El docente selecciona un grupo y un periodo para consultar indicadores, cada uno con su propia base de cálculo. | **Recursos de investigación · Azul eléctrico.** El investigador accede a sus encuestas y diapositivas desde el celular. |

## Instalación de la entrega universitaria

La instalación usa Svelte para la interfaz, FastAPI para la API, PostgreSQL con pgvector para los datos y el índice, y Caddy para servir la aplicación y la portada. El archivo `VERSION-ENTREGA.txt` identifica el corte técnico descrito en la monografía y la huella del manifiesto del corpus. Consulte [las fuentes y los permisos por obra](contenido/corpus/FUENTES.md).

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

Si la VPS ya cuenta con un proxy inverso institucional (servidor que recibe las conexiones HTTPS y las pasa a la aplicación), elija el perfil de VPS compartida. Defina `DIDAXIA_DOMINIO_APP`, `DIDAXIA_DOMINIO_PUBLICO` y `DIDAXIA_DOMINIO_ALIAS` con los nombres DNS respectivos, y `DIDAXIA_PUERTO_HTTP` con el puerto asignado. El proxy termina HTTPS, conserva el encabezado `Host` y reenvía al puerto de bucle local que publica Compose. Mantenga `ORIGEN_APLICACION` y `ORIGEN_PUBLICO` como las direcciones HTTPS que usa el navegador. Revise también `frontend/publico/robots.txt` y `llms.txt`: describen el sitio original y se deben adaptar si la Universidad decide indexar su portada. Para una entrega de acceso restringido, la Universidad controla el acceso en el borde; `robots.txt` no controla quién puede entrar.

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

Compose espera a PostgreSQL, ejecuta las migraciones versionadas en `infraestructura/esquema/` y carga los fragmentos admisibles de `contenido/corpus/fragmentos/` con el catálogo `FUENTES.md`. El índice se guarda en PostgreSQL; no se distribuye una base precargada. Si la ingesta falla, se bloquea el inicio del backend. Después se sirve el frontend por Caddy. `migraciones`, `ingesta` y `frontend-build` deben quedar en estado `Exited (0)`; son trabajos de una sola pasada.

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
