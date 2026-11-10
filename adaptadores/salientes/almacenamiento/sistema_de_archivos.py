r"""
sistema_de_archivos.py — La custodia privada, sobre un volumen · `D3`
=======================================================================

El `PuertoAlmacenamientoPrivado` que **sí guarda**. Sustituye a
`no_configurado.py` cuando el despliegue declara dónde vive la carpeta privada,
y no antes: sin esa declaración se conserva el adaptador que falla cerrado.

De dónde sale la decisión
-------------------------------------
`ESTADO-ACTUAL.md` §10.4 y la decisión D3 del equipo: *«la primera opción
solicitada es un volumen persistente y privado en la VPS institucional, montado
fuera del árbol de código y de la capa escribible de los contenedores»*. Drive
institucional queda como alternativa **si** la infraestructura no admite ese
volumen, y por eso aquí no hay una línea de Drive: implementar las dos habría
sido implementar la que todavía no se eligió.

Lo que este adaptador **no** decide: dónde está el volumen. Eso es
`ALMACENAMIENTO_PRIVADO_RUTA`, y el mismo código sirve para los cuatro sitios
donde tiene que servir —una carpeta temporal en las pruebas, una carpeta privada
fuera del repositorio en la demostración, un volumen montado dentro del
contenedor en producción y el volumen institucional el día que exista— sin tocar
el dominio ni ninguna ruta HTTP.

Por qué la raíz no se crea sola
-------------------------------------------
Un `mkdir(parents=True)` silencioso convierte una variable mal escrita en una
carpeta nueva y vacía: el sistema arrancaría, aceptaría autorizaciones firmadas
por representantes legales y las escribiría **fuera** del volumen que alguien
respalda. Eso es el éxito parcial que `EQ-024` prohíbe, con la peor carga útil
posible. Aquí la raíz **tiene que existir** y ser un directorio con lectura y
escritura; si no, `ConfiguracionInvalida` y el despliegue se queda con el
adaptador que no acepta nada.

Los dos subdirectorios de trabajo —`provisionales/` y `confirmados/`— sí se
crean, y la diferencia no es un capricho: son estructura interna de este
adaptador dentro de una raíz que alguien ya provisionó y montó a propósito.

Estructura física
-----------------------

    <raíz privada>/
      provisionales/   c1-<32 hex>.bin   ← reservado, todavía no es evidencia
      confirmados/     c1-<32 hex>.bin   ← evidencia definitiva

Nada más. La separación es por **directorio** y no por un sufijo en el nombre ni
por una columna: mover un archivo entre dos directorios es la única promoción
atómica que ofrece el sistema de archivos, y cualquier otra representación del
estado obligaría a escribir dos cosas y a poder quedarse a medias entre ellas.

La referencia, y por qué ignora `sujeto_google` e `intento`
------------------------------------------------------------------------
El puerto los pasa *«para que el adaptador pueda organizar lo que guarda»*, y
este adaptador decide **no** organizar nada con ellos. Son datos personales: el
sujeto de Google identifica a una persona y el intento cuenta sus fracasos.
Derivar de ellos el nombre —aunque fuera por una huella— dejaría en el
directorio una estructura que responde «¿cuántas veces intentó cargar esta
persona?» a cualquiera que consiga listarlo, y el encargo de D3 prohíbe
exactamente eso: nombres sin correo, sin sujeto, sin edad, sin intento, sin
nombre y sin identificador de clase.

Lo que queda es `c1-` más 128 bits de `os.urandom`. Es opaco, no es una URL —el
tipo del dominio y el CHECK de `representante_evidencia` rechazan `http(s)://`—,
no colisiona y no se puede adivinar. Y `c1` nombra el formato, no el contenido:
el día que la disposición cambie, un prefijo distinto permite distinguir las dos
sin mirar dentro.

Que la referencia sea estable la aporta PostgreSQL, que la guarda. Este
adaptador sólo tiene que encontrar el mismo archivo con ella después de un
reinicio, y lo hace porque el nombre **es** la referencia.

Atomicidad, en las tres operaciones que escriben
-----------------------------------------------------------------
- `reservar()` escribe en un temporal del **mismo directorio** —mismo volumen,
  para que la promoción no sea una copia—, hace `fsync`, y sólo entonces reclama
  el nombre definitivo con `os.link()`. `link` es la única primitiva que en
  POSIX **y** en Windows es atómica y **falla** si el destino ya existe: `rename`
  sobrescribe en POSIX y `replace` sobrescribe en los dos. Una escritura que se
  corta a la mitad deja un temporal, que no se enumera y no se sirve; nunca una
  reserva válida. **Si el montaje no admite `link`, la custodia falla cerrada**
  — no hay ningún camino alternativo, porque todos pueden sobrescribir.
- `confirmar()` mueve el archivo de `provisionales/` a `confirmados/` con un
  `rename` sobre un destino que se comprobó ausente. No copia y borra: una copia
  puede quedarse a medias y dejar dos archivos.
- `retirar()` sólo borra dentro de `provisionales/`. No hay ninguna ruta de
  código de este módulo que borre en `confirmados/`, y es deliberado: borrar
  evidencia es la cascada que el cierre V-B reserva a la decisión humana.

Rutas: lo que se acepta y lo que se comprueba después
--------------------------------------------------------------------
Dos barreras, y hacen falta las dos.

1. **La forma de la referencia**, con una expresión regular anclada
   (`_REFERENCIA`). `..`, `/`, `\`, `C:`, `\\servidor\recurso`, un `%2e%2e`
   decodificado, un byte nulo o una longitud distinta no son 32 dígitos
   hexadecimales, así que no llegan a componer ninguna ruta. **No existe en este
   módulo una concatenación de ruta con entrada sin validar**: `_ruta()` valida
   antes de tocar el separador.
2. **La contención real**, con `os.path.realpath`. La primera barrera basta
   contra un nombre malicioso y **no** contra un enlace: alguien con acceso al
   volumen puede dejar en `confirmados/` un symlink —o, en Windows, una unión o
   punto de reanálisis, que `os.path.islink()` **no** reconoce— apuntando fuera.
   Por eso cada operación resuelve la ruta y comprueba que sigue colgando de la
   raíz resuelta; si no, se comporta como si el archivo no estuviera.

Permisos y cifrado
--------------------------
En POSIX se piden `0700` para los directorios y `0600` para los archivos. En
Windows eso **no** es equivalente: `os.chmod` sólo mueve el bit de sólo lectura y
no toca la ACL, así que este módulo no finge lo contrario —lo intenta, y no
afirma nada—. La restricción real de la raíz es una ACL o unos permisos de
montaje que administra quien opera el volumen, no Python: crear cuentas o
cambiar dueños desde aquí sería administrar el sistema operativo desde una
aplicación web.

**No hay cifrado aplicativo.** Inventar uno significaría inventar dónde vive su
clave, y una clave que el proceso puede leer no protege del acceso al volumen,
que es la amenaza real. El cifrado en reposo corresponde al volumen o a la VPS.

Lo que no sale de aquí
--------------------------------
Ni la raíz, ni una ruta, ni un nombre de archivo, ni la referencia, ni el
contenido aparecen en el texto de ninguna excepción de este módulo. Un error
acaba en una consola, en un registro y en una captura pegada en un chat, y la
ruta del volumen donde viven las autorizaciones firmadas de menores de edad no
tiene por qué estar en ninguno de los tres. `/api/salud` publica banderas, y las
compone `rutas/salud.py` a partir de `estado_publicable()`.


"""

from __future__ import annotations

import contextlib
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path

from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoDisponible,
    DocumentoAusente,
    DocumentoPendienteDeConfirmacion,
)

#: La variable que dice dónde está el volumen privado. Una sola, y sin valor por
#: defecto: un defecto convertiría «no configurado» en «configurado en un sitio
#: que nadie eligió».
VARIABLE_RUTA = "ALMACENAMIENTO_PRIVADO_RUTA"

#: Los dos estados, y sus dos directorios. Ver el docstring del módulo.
PROVISIONALES = "provisionales"
CONFIRMADOS = "confirmados"

#: El sufijo del archivo. No lleva `.pdf` a propósito: el tipo lo declara la
#: fila de PostgreSQL y lo fija la ruta que lo sirve (`TIPO_DEL_ARCHIVO`).
#: Escribirlo también aquí crearía una segunda fuente de verdad que el día que
#: divergiera haría servir un tipo por el nombre del archivo del volumen.
SUFIJO = ".bin"

#: El prefijo del formato de referencia. Ver el docstring del módulo.
PREFIJO = "c1-"

#: Cuántos bytes de azar lleva una referencia. 16 bytes son 128 bits: con ellos,
#: la probabilidad de que dos reservas coincidan es indistinguible de cero, y
#: aun así `reservar()` no se apoya en esa probabilidad — reclama el nombre con
#: una operación que falla si ya existe.
BYTES_DE_AZAR = 16

#: La forma EXACTA de una referencia aceptable. Anclada por los dos extremos:
#: `re.match` sin `$` habría aceptado `c1-<32 hex>/../../etc/passwd`.
_REFERENCIA = re.compile(rf"^{re.escape(PREFIJO)}[0-9a-f]{{{BYTES_DE_AZAR * 2}}}$")

#: El nombre EXACTO de un archivo de custodia dentro de uno de los dos
#: directorios. Es lo que `pendientes()` enumera, y por eso los temporales
#: llevan otro prefijo y otro sufijo: no pueden coincidir con esto.
_ARCHIVO = re.compile(
    rf"^{re.escape(PREFIJO)}[0-9a-f]{{{BYTES_DE_AZAR * 2}}}{re.escape(SUFIJO)}$"
)

#: Cómo se llaman los temporales de este adaptador. El punto inicial los oculta
#: en POSIX, y el sufijo los deja fuera de `_ARCHIVO`. Sirve además para saber
#: cuáles son **propios**: la limpieza de un fallo no borra nada que no encaje.
PREFIJO_TEMPORAL = ".parcial-"
SUFIJO_TEMPORAL = ".tmp"

#: Permisos POSIX. Dueño y nadie más. En Windows no significan lo mismo y este
#: módulo no afirma que sí — ver el docstring.
MODO_DIRECTORIO = 0o700
MODO_ARCHIVO = 0o600

#: Cuántas veces se vuelve a sortear una referencia si el nombre ya estaba
#: tomado. Con 128 bits esto no ocurre por azar; ocurre si alguien dejó a mano
#: un archivo con ese nombre, y entonces reintentar tres veces y rendirse es
#: mejor que un bucle infinito.
INTENTOS_DE_NOMBRE = 3


class ConfiguracionInvalida(ValueError):
    """`ALMACENAMIENTO_PRIVADO_RUTA` no describe una custodia utilizable.

    Es un error de **configuración**, no de almacenamiento, y por eso no cuelga
    de `ErrorDeAlmacen`: quien lo recibe está componiendo la aplicación, no
    atendiendo una petición. `aplicacion.py` lo traduce a un faltante operativo y
    se queda con el adaptador que no acepta evidencias.

    El mensaje describe **qué** falla y nunca **dónde**: la ruta del volumen
    privado no entra en un texto de error. Ver el docstring del módulo.
    """


def _ruta_contenida(candidata: Path, raiz_resuelta: str) -> bool:
    """Si `candidata` sigue colgando de la raíz **después** de resolver enlaces.

    ⚠️ **`os.path.islink()` no basta, y en Windows es directamente insuficiente.**
    Una unión de directorio (`mklink /J`) creada sin privilegios de administrador
    devuelve `islink() == False` y aun así redirige fuera del volumen. Lo que sí
    la ve es `realpath`, que sigue la cadena entera de enlaces y puntos de
    reanálisis.

    Se resuelve también cuando el archivo todavía no existe —`realpath` resuelve
    el prefijo que sí existe—, que es lo que hace utilizable esta comprobación
    antes de crear una reserva.

    `os.path.commonpath` en vez de comparar cadenas con `startswith`: aquello
    aceptaría `/volumen/privado-de-otro` como si colgara de `/volumen/privado`.
    """
    try:
        resuelta = os.path.realpath(candidata)
    except OSError:
        return False
    if resuelta == raiz_resuelta:
        return True
    try:
        return os.path.commonpath([resuelta, raiz_resuelta]) == raiz_resuelta
    except ValueError:
        # Unidades distintas en Windows. No comparten prefijo: está fuera.
        return False


def _es_archivo_propio(ruta: Path, raiz_resuelta: str) -> bool:
    """Si esa ruta es un archivo regular **de esta custodia**, sin seguir enlaces.

    Las dos mitades importan. `lstat` distingue un archivo regular de un
    directorio, de un enlace y de un dispositivo sin resolverlo, así que un
    symlink colocado con el nombre correcto no pasa por archivo. Y la contención
    cubre lo que `lstat` no ve: una unión de Windows, que no es un enlace para
    `stat` y sí redirige.
    """
    try:
        info = ruta.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode):
        return False
    return _ruta_contenida(ruta, raiz_resuelta)


def _permisos(ruta: Path, modo: int) -> None:
    """Pide los permisos y **no promete** haberlos conseguido.

    En POSIX `chmod` hace exactamente lo que dice. En Windows mueve el bit de
    sólo lectura y no toca la ACL, así que el resultado no es equivalente y este
    módulo no lo presenta como tal. Un fallo no interrumpe la operación: la
    custodia real la sostiene el permiso del volumen, no esta llamada.
    """
    with contextlib.suppress(OSError):
        os.chmod(ruta, modo)


class AlmacenamientoEnSistemaDeArchivos:
    """`PuertoAlmacenamientoPrivado` sobre un directorio privado del anfitrión.

    Se construye con una raíz **ya validada**. El constructor no lee el entorno:
    quien lo hace es `desde_entorno()`, una sola vez, en la composición. Un
    adaptador que releyera la variable en cada operación podría cambiar de
    volumen a mitad de un protocolo de dos fases.
    """

    def __init__(self, raiz: Path | str) -> None:
        raiz = Path(raiz)
        if not raiz.is_absolute():
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada tiene que ser una ruta absoluta"
            )
        if not raiz.is_dir():
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada no existe o no es un directorio; "
                "no se crea sola"
            )
        self._raiz = raiz
        # Se resuelve UNA vez y se conserva: la raíz puede ser legítimamente un
        # punto de montaje o un enlace —eso es lo normal en un volumen—, y lo
        # que se comprueba después es que cada archivo cuelgue de lo que la raíz
        # resuelve, no de lo que se escribió en la variable.
        self._raiz_resuelta = os.path.realpath(raiz)
        self._provisionales = raiz / PROVISIONALES
        self._confirmados = raiz / CONFIRMADOS
        self._preparar()

    # ── construcción ────────────────────────────────────────────────────

    def _preparar(self) -> None:
        """Crea los dos directorios de trabajo y comprueba que se puede escribir.

        Los subdirectorios sí se crean —son estructura interna dentro de una raíz
        que alguien ya provisionó—, y la comprobación de escritura se hace
        **aquí y no en la primera petición**: una custodia que sólo se descubre
        inservible al recibir el primer PDF firmado ya rechazó a alguien.

        La comprobación es no destructiva y no deja rastro: crea y borra un
        temporal propio en `provisionales/`.
        """
        for directorio in (self._provisionales, self._confirmados):
            try:
                directorio.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfiguracionInvalida(
                    "no se pudieron preparar los directorios de la custodia privada "
                    f"({exc.__class__.__name__})"
                ) from None
            _permisos(directorio, MODO_DIRECTORIO)
        try:
            descriptor, temporal = tempfile.mkstemp(
                dir=self._provisionales, prefix=PREFIJO_TEMPORAL, suffix=SUFIJO_TEMPORAL
            )
        except OSError as exc:
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada no admite escritura "
                f"({exc.__class__.__name__})"
            ) from None
        os.close(descriptor)
        os.unlink(temporal)

    # ── rutas ───────────────────────────────────────────────────────────

    def _ruta(self, referencia: str, directorio: Path) -> Path | None:
        """La ruta de esa referencia, o `None` si la referencia no es aceptable.

        ⚠️ **Aquí es donde no hay concatenación con entrada sin validar.** El
        separador sólo se toca después de que `_REFERENCIA` haya aceptado la
        cadena entera, y esa expresión está anclada por los dos extremos.

        Devuelve `None` en vez de levantar porque cada operación decide qué
        significa: para `recuperar()` es «no está», para `retirar()` es `False`.
        Una excepción propia habría obligado a traducirla cuatro veces.
        """
        if not isinstance(referencia, str) or not _REFERENCIA.match(referencia):
            return None
        ruta = directorio / f"{referencia}{SUFIJO}"
        if not _ruta_contenida(ruta, self._raiz_resuelta):
            return None
        return ruta

    # ── protocolo de dos fases ──────────────────────────────────────────

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        """Deja una carga provisional y devuelve su referencia opaca.

        `sujeto_google` e `intento` se reciben por contrato y **no se usan**: ver
        el docstring del módulo. Nombrarlos aquí y no usarlos es la forma de que
        el día que alguien quiera organizarlo por persona tenga delante el motivo
        por el que no se hace.

        La secuencia es escribir → `fsync` → reclamar el nombre. Al revés —crear
        el nombre definitivo y escribir dentro— una interrupción dejaría una
        reserva válida con un PDF truncado, que es peor que ninguna reserva:
        `pendientes()` la enumeraría y un operador la promovería.
        """
        del sujeto_google, intento  # ver el docstring
        try:
            descriptor, temporal = tempfile.mkstemp(
                dir=self._provisionales, prefix=PREFIJO_TEMPORAL, suffix=SUFIJO_TEMPORAL
            )
        except OSError:
            raise AlmacenamientoNoDisponible(
                "la custodia privada no admite escribir la reserva"
            ) from None

        ruta_temporal = Path(temporal)
        try:
            with os.fdopen(descriptor, "wb") as archivo:
                archivo.write(contenido)
                archivo.flush()
                # `fsync` y no sólo `flush`: `flush` vacía el búfer de Python al
                # del sistema operativo, y lo que sobrevive a un corte de luz es
                # lo que llegó al disco. Sin esto, la promoción sería atómica
                # sobre un contenido que puede no estar.
                os.fsync(archivo.fileno())
            _permisos(ruta_temporal, MODO_ARCHIVO)
            referencia = self._reclamar(ruta_temporal)
        except OSError:
            self._descartar_temporal(ruta_temporal)
            raise AlmacenamientoNoDisponible(
                "no se pudo completar la reserva en la custodia privada"
            ) from None
        except BaseException:
            # Incluye `AlmacenamientoNoDisponible` de `_reclamar()` y cualquier
            # interrupción: el temporal es nuestro y no se queda tirado.
            self._descartar_temporal(ruta_temporal)
            raise
        self._sincronizar_directorio(self._provisionales)
        return referencia

    def _reclamar(self, ruta_temporal: Path) -> str:
        """Sortea una referencia libre y le enlaza el temporal ya escrito.

        `os.link()` es **la única** primitiva que se usa aquí: es atómica y
        levanta `FileExistsError` si el destino existe, tanto en POSIX como en
        NTFS. `os.rename()` sobrescribiría en silencio en POSIX y
        `Path.replace()` en los dos.

        ⚠️ **No hay respaldo, y su ausencia es la garantía.** Hubo uno —
        `destino.exists()` seguido de `os.rename()`— para montajes sin enlaces
        duros. Entre mirar y renombrar hay una ventana, y `rename` sobrescribe:
        bastaba con que el nombre apareciera en ese hueco para que una
        autorización firmada por un representante legal reemplazara a otra sin
        que nada lo dijera. Un sistema de archivos que no admita `link` deja la
        custodia **cerrada**, que es la respuesta correcta: `EQ-024` prohíbe el
        éxito parcial, y aceptar una evidencia que puede pisar a otra lo sería.
        """
        ultimo: OSError | None = None
        for _ in range(INTENTOS_DE_NOMBRE):
            referencia = f"{PREFIJO}{secrets.token_hex(BYTES_DE_AZAR)}"
            destino = self._provisionales / f"{referencia}{SUFIJO}"
            try:
                os.link(ruta_temporal, destino)
            except FileExistsError as exc:
                # El nombre estaba tomado. Con 128 bits no ocurre por azar, así
                # que se vuelve a sortear y, si insiste, se falla cerrado.
                ultimo = exc
                continue
            except OSError as exc:
                # El montaje no admite enlaces duros, o falló por otra causa. No
                # se intenta nada más: cualquier alternativa puede sobrescribir.
                raise AlmacenamientoNoDisponible(
                    "la custodia privada no admite reclamar un nombre de forma "
                    "atómica; no se acepta la evidencia en vez de arriesgar un "
                    "reemplazo"
                ) from exc
            os.unlink(ruta_temporal)
            return referencia
        raise AlmacenamientoNoDisponible(
            "no se pudo reservar un nombre libre en la custodia privada"
        ) from ultimo

    def _descartar_temporal(self, ruta: Path) -> None:
        """Borra un temporal **propio**. Nunca otra cosa.

        La comprobación del nombre no es paranoia decorativa: esta función se
        llama desde el camino de fallo, que es donde una variable puede traer lo
        que nadie esperaba. Un `unlink` sin mirar sería la única operación de
        este módulo capaz de borrar algo que no creó.
        """
        nombre = ruta.name
        if not (nombre.startswith(PREFIJO_TEMPORAL) and nombre.endswith(SUFIJO_TEMPORAL)):
            return
        if not _ruta_contenida(ruta, self._raiz_resuelta):
            return
        with contextlib.suppress(OSError):
            os.unlink(ruta)

    def _sincronizar_directorio(self, directorio: Path) -> None:
        """`fsync` sobre el directorio, donde el sistema operativo lo permite.

        El contenido del archivo ya está en disco; esto es lo que hace que su
        **entrada de directorio** también lo esté. En Windows no se puede abrir
        un directorio con `os.open`, así que allí no ocurre y no se finge que sí:
        el sistema de archivos da su propia garantía y la alternativa —afirmar
        una durabilidad que no se pidió— sería peor.
        """
        try:
            descriptor = os.open(directorio, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    def confirmar(self, referencia: str) -> None:
        """Promueve la carga provisional a evidencia definitiva.

        **Repetir `confirmar()` es correcto y no hace nada.** La segunda llamada
        encuentra el archivo ya en `confirmados/` y vuelve sin tocarlo. Es la
        definición que hace posible el reintento y la que hace que dos hilos
        concurrentes no se estorben: uno mueve, el otro descubre que ya está
        movido, y ninguno de los dos informa un fallo que no ocurrió.

        Confirmar algo que no existe **sí** falla: `DocumentoAusente`. Devolver
        éxito ahí diría que hay evidencia definitiva donde no hay ningún archivo.

        Y si estuvieran los dos —provisional y confirmado con la misma
        referencia— no se sobrescribe nada: es una discrepancia que un operador
        tiene que mirar, y elegir por él cuál de los dos es la evidencia sería
        exactamente la decisión que no le corresponde a este módulo.
        """
        origen = self._ruta(referencia, self._provisionales)
        destino = self._ruta(referencia, self._confirmados)
        if origen is None or destino is None:
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            )

        confirmado = _es_archivo_propio(destino, self._raiz_resuelta)
        provisional = _es_archivo_propio(origen, self._raiz_resuelta)
        if confirmado and not provisional:
            return
        if confirmado and provisional:
            raise AlmacenamientoNoDisponible(
                "la custodia privada tiene esa referencia a la vez como reserva y "
                "como evidencia confirmada: hace falta reconciliarla"
            )
        if not provisional:
            # ⚠️ **Se vuelve a mirar el destino, y no es redundante.** Las dos
            # comprobaciones de arriba no son atómicas entre sí: otro hilo pudo
            # completar la promoción entre la primera y la segunda, y entonces
            # aquélla vio «no confirmado» y ésta ve «ya no es provisional». Sin
            # este segundo vistazo, ese entrelazado —que una prueba de ocho
            # hilos reproduce— respondía `DocumentoAusente` sobre una evidencia
            # perfectamente confirmada, y la ruta HTTP lo habría traducido a un
            # 503 que le dice al titular que su carga no quedó registrada.
            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            )

        try:
            os.rename(origen, destino)
        except FileNotFoundError:
            # Otro hilo la movió entre la comprobación y esta línea. Si acabó
            # donde tenía que acabar, la promoción ocurrió: informar un fallo
            # dejaría la ruta HTTP respondiendo 503 sobre una evidencia bien
            # confirmada, y el titular creería perdida una carga que sí entró.
            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            ) from None
        except OSError:
            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise AlmacenamientoNoDisponible(
                "no se pudo promover la reserva a evidencia confirmada"
            ) from None
        self._sincronizar_directorio(self._confirmados)

    def retirar(self, referencia: str) -> bool:
        """Borra una carga **provisional**. `True` si existía.

        `False` cuando no había nada, y eso no es un éxito disfrazado: el
        contrato del puerto dice literalmente «`True` si existía», así que
        distinguirlo es lo que pide. Quien compensa una fila que no entró
        necesita saber si de verdad retiró algo.

        No hay ninguna rama de esta función que pueda alcanzar `confirmados/`.
        """
        ruta = self._ruta(referencia, self._provisionales)
        if ruta is None:
            return False
        if not _es_archivo_propio(ruta, self._raiz_resuelta):
            # Incluye el caso en que alguien dejó ahí un enlace con ese nombre:
            # no se sigue, y no se borra su destino.
            return False
        try:
            os.unlink(ruta)
        except FileNotFoundError:
            return False
        except OSError:
            raise AlmacenamientoNoDisponible(
                "no se pudo retirar la reserva de la custodia privada"
            ) from None
        return True

    def recuperar(self, referencia: str) -> bytes:
        """Los bytes de una carga **confirmada**, y sólo de ésa.

        Los cuatro desenlaces del puerto, en el orden que impone el contrato:
        confirmada → bytes; provisional →
        `DocumentoPendienteDeConfirmacion`; ausente → `DocumentoAusente`; avería
        → `AlmacenamientoNoDisponible`. Ninguno devuelve `b""`.

        Se abre con `lstat` comprobado antes, no con un `open()` a secas: un
        enlace colocado con el nombre correcto serviría un archivo de fuera del
        volumen a un investigador, con la apariencia de una evidencia
        custodiada.
        """
        confirmado = self._ruta(referencia, self._confirmados)
        provisional = self._ruta(referencia, self._provisionales)
        if confirmado is None or provisional is None:
            raise DocumentoAusente(
                "la custodia privada no tiene ningún archivo bajo esa referencia"
            )
        if _es_archivo_propio(confirmado, self._raiz_resuelta):
            try:
                return confirmado.read_bytes()
            except OSError:
                raise AlmacenamientoNoDisponible(
                    "no se pudo leer el archivo de la custodia privada"
                ) from None
        if _es_archivo_propio(provisional, self._raiz_resuelta):
            raise DocumentoPendienteDeConfirmacion(
                "la carga sigue siendo provisional: no se confirmó ni se retiró"
            )
        raise DocumentoAusente(
            "la custodia privada no tiene ningún archivo bajo esa referencia"
        )

    def pendientes(self) -> tuple[str, ...]:
        """Las referencias reservadas que no se confirmaron ni se retiraron.

        Devuelve **referencias**, nunca rutas: quien vigila las reservas
        pendientes tiene que poder pegar el resultado en un informe sin publicar
        dónde vive el volumen.

        Enumera sólo lo que encaja en `_ARCHIVO` y es un archivo regular
        contenido en la raíz. Eso deja fuera, sin necesidad de nombrarlos uno a
        uno, los temporales de una escritura a medias, cualquier archivo que
        alguien dejara ahí a mano, los directorios y los enlaces.

        El orden es alfabético y por tanto determinista: dos llamadas seguidas
        sobre el mismo estado devuelven lo mismo, y una comparación en una prueba
        o en un informe no depende del orden en que el sistema de archivos
        devuelva las entradas.
        """
        try:
            entradas = list(os.scandir(self._provisionales))
        except OSError:
            raise AlmacenamientoNoDisponible(
                "no se pudo enumerar las reservas de la custodia privada"
            ) from None
        referencias = []
        for entrada in entradas:
            if not _ARCHIVO.match(entrada.name):
                continue
            if not entrada.is_file(follow_symlinks=False):
                continue
            if not _ruta_contenida(Path(entrada.path), self._raiz_resuelta):
                continue
            referencias.append(entrada.name[: -len(SUFIJO)])
        return tuple(sorted(referencias))

    def esta_configurado(self) -> bool:
        """Sí: este adaptador sólo existe si la configuración se validó.

        No escribe nada para responder —`_preparar()` ya comprobó la escritura al
        construirlo— y no publica ningún valor. Una versión que tanteara el disco
        en cada consulta habría convertido `/api/salud` en escritura.
        """
        return True

    # ── lo que la salud puede publicar ──────────────────────────────────

    def estado_publicable(self) -> dict:
        """Banderas para `/api/salud`. **Ningún valor.**

        Ni la raíz, ni un nombre, ni una referencia. `disponible` es una
        comprobación no destructiva —que los dos directorios siguen siendo
        directorios legibles— y `reservas_pendientes` es un conteo, que dice si
        hay que mirar sin decir qué mirar.

        Está aquí y no en `rutas/salud.py` porque es el adaptador quien sabe qué
        de lo suyo es publicable; la ruta sólo lo copia al cuerpo, y así no puede
        inventarse un campo que revele algo.
        """
        try:
            disponible = self._provisionales.is_dir() and self._confirmados.is_dir()
        except OSError:
            disponible = False
        cuerpo = {
            "configurado": True,
            "tipo": "sistema_de_archivos",
            "disponible": disponible,
        }
        try:
            cuerpo["reservas_pendientes"] = len(self.pendientes())
        except AlmacenamientoNoDisponible:
            cuerpo["disponible"] = False
        return cuerpo


def desde_entorno(entorno: dict | None = None) -> AlmacenamientoEnSistemaDeArchivos | None:
    """El adaptador si la variable declara una custodia utilizable; `None` si no.

    Tres respuestas y no dos, y la composición las distingue:

    - **variable ausente** → `None`, sin excepción. No es una avería: es un
      despliegue que todavía no tiene custodia, exactamente como estaba el
      sistema antes de D3.
    - **variable presente y utilizable** → el adaptador.
    - **variable presente e inutilizable** → `ConfiguracionInvalida`. Falla
      cerrado: quien la escribió creía haber configurado algo, y caer en
      silencio al adaptador que no acepta nada le habría dejado un 503 sin
      motivo. Lo que **no** ocurre es caer a memoria ni escribir dentro del
      repositorio.

    Se lee el entorno **aquí**, una vez, y no dentro del adaptador: ver el
    docstring de `AlmacenamientoEnSistemaDeArchivos`.
    """
    entorno = os.environ if entorno is None else entorno
    bruto = (entorno.get(VARIABLE_RUTA) or "").strip()
    if not bruto:
        return None
    return AlmacenamientoEnSistemaDeArchivos(Path(bruto))
