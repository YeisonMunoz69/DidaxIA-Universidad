"""
resend.py — `PuertoNotificacion` contra la API HTTP de Resend (`D2`)
=====================================================================

El canal que `EQ-022` pide y `EQ-024` acota: *«Resend será un canal de
notificación, no una dependencia del diagnóstico ni una garantía de
disponibilidad»*.

Avisos automáticos y comunicación institucional
---------------------------------------------------
`D2` introdujo los avisos transaccionales: confirmar al titular una decisión,
avisarle que su solicitud de supresión quedó registrada y alertar al canal
operativo. `EQ-040` amplía el borde con comunicación iniciada por un
investigador, confirmada y auditada antes de enviarse. Este adaptador no sabe
cuál de esos casos está transportando y no debe saberlo: recibe destinatario,
asunto, texto, HTML, adjuntos y clave. Quién decide si corresponde enviar sigue
siendo el caso de uso.

Por eso aquí no hay plantillas, ni jerarquía de mensajes, ni tipos de aviso.

Por qué la API HTTP y no el SDK
------------------------------------------
El mismo motivo que `adaptadores/salientes/generacion/deepseek.py` dejó escrito
para DeepSeek, más uno propio: **el SDK de Resend guarda la clave en un módulo
global mutable** (`resend.api_key = ...`). Un secreto en estado global es un
secreto que cualquier import posterior puede leer o pisar, y en una suite que
compone la aplicación muchas veces sería además una fuente de interferencia
entre pruebas. Aquí la clave vive en el transporte, que vive en la instancia.

Por qué `urllib` y no `httpx`
-------------------------------------
Porque la dependencia de producción apropiada **ya existe**: `urllib` es de la
biblioteca estándar, es lo que este árbol usa para hablar con el proveedor de
generación desde `PM-B14`, y trae el mismo patrón de transporte inyectable que
estas pruebas necesitan. Añadir `httpx` a `requirements.txt` habría metido una
dependencia nueva en la imagen productiva para hacer un `POST` con cuerpo JSON
—y `ESTADO-ACTUAL.md` §4.5 pide reutilizar el mecanismo existente antes de abrir
uno paralelo—.

No se reutiliza el `TransporteHTTP` de `deepseek.py` porque su firma no sirve:
allí las cabeceras se fijan al construir, y aquí la clave de idempotencia
**cambia en cada envío**. Compartir el tipo habría obligado a ensanchar el del
generador con un parámetro que no usa.

Qué se registra, y qué no
----------------------------------
Se registra la **clave opaca** del aviso, el estado HTTP normalizado y el
identificador que devuelve Resend cuando existe. No se registran el cuerpo de la
respuesta, el correo, el texto, la cabecera `Authorization`, la clave de API ni
ninguna cadena de conexión. El identificador de Resend sirve para buscar el
envío en su panel; el correo del titular no aporta nada al diagnóstico y lo
convertiría en un dato personal más que conservar.

El resultado, en una frase
-----------------------------------
**`True` sólo con un 2xx que traiga un identificador de Resend.** Un 4xx, un
5xx, un tiempo agotado, un fallo de transporte, un JSON ilegible o una respuesta
sin identificador devuelven `False`. Nunca levanta y **nunca reintenta dentro de
la petición**: un reintento en bucle dejaría al titular esperando mientras el
trámite ya está confirmado.

⚠️ «Nunca levanta» incluye lo que nadie previó
------------------------------------------------------
La primera versión de `D2` traducía los tres fallos que `_TransporteUrllib` sabe
nombrar y daba por hecho que no había más. Los había: **cualquier otra excepción
del transporte cruzaba hasta el caso de uso**, que ya tenía su escritura
confirmada, y la convertía en un 500 — el «éxito parcial» que `EQ-024` prohíbe
comunicar. Lo encontró la revisión independiente de `bd2b66f` reproduciéndolo con
un transporte que levanta `RuntimeError`.

Ahora `avisar()` atrapa `Exception` alrededor de la llamada al transporte y
devuelve `False`. **`BaseException` no**: `KeyboardInterrupt`, `SystemExit` y
`asyncio.CancelledError` tienen que seguir subiendo, porque un adaptador de
correo que se tragara un Ctrl-C impediría apagar el proceso.


"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_LOG = logging.getLogger(__name__)

#: El único camino de la API que este adaptador usa. Sin lotes, sin webhooks y
#: sin plantillas alojadas: se manda un correo por llamada, también cuando una
#: acción del investigador contiene varios destinatarios.
URL_DE_ENVIO = "https://api.resend.com/emails"

#: Quién dice ser este cliente. Explícito y versionado a mano: si algún día hay
#: que distinguir en el panel de Resend qué versión del backend produjo un
#: envío, este es el único sitio que lo dice.
AGENTE_DE_USUARIO = "DidaxIa-notificaciones/1.0"

#: `T-01` fija cinco segundos para PostgreSQL y aquí vale el mismo criterio: un
#: aviso que no sale en cinco segundos no va a salir, y esperar más bloquea la
#: respuesta de un trámite **que ya está confirmado**.
PLAZO_DE_ENVIO_S = 5.0


@dataclass(frozen=True, slots=True)
class RespuestaHTTP:
    """Lo que el transporte devuelve, ya sin excepciones dentro.

    `estado` es el código HTTP y **0 significa que no hubo respuesta** —tiempo
    agotado o fallo de conexión—; entonces `motivo` dice cuál, con un texto del
    propio transporte y no con la excepción original. Que la traducción ocurra
    en el transporte y no en el adaptador es la regla **N2**: el tipo del borde
    —una `URLError`, un `TimeoutError`— no cruza hacia dentro.
    """

    estado: int
    cuerpo: bytes = b""
    motivo: str = ""


@runtime_checkable
class TransporteHTTP(Protocol):
    """Lo que el adaptador necesita de la red, y nada más.

    Existe para que las pruebas puedan comprobar los seis desenlaces —2xx, 4xx,
    5xx, tiempo agotado, fallo de transporte y respuesta inválida— **sin llegar
    a Internet**, que es una condición del encargo y no una comodidad.
    """

    def enviar(self, cuerpo: bytes, *, idempotencia: str) -> RespuestaHTTP:
        """`POST` del cuerpo JSON. No levanta: reporta en el resultado."""
        ...


class _TransporteUrllib:
    """El transporte real, sobre la biblioteca estándar.

    La clave vive aquí —en la instancia— y no en un módulo: ver el docstring del
    módulo sobre el estado global del SDK.
    """

    def __init__(self, url: str, clave: str, plazo_s: float) -> None:
        self._url = url
        self._clave = clave
        self._plazo_s = plazo_s

    def enviar(self, cuerpo: bytes, *, idempotencia: str) -> RespuestaHTTP:
        # Se importa dentro por la misma razón que `conexion.py` importa
        # `psycopg` dentro: el módulo se puede leer e inspeccionar sin nada
        # montado. Aquí además `urllib` es estándar y siempre está.
        import urllib.error  # noqa: PLC0415
        import urllib.request  # noqa: PLC0415

        peticion = urllib.request.Request(
            self._url,
            data=cuerpo,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._clave}",
                "Content-Type": "application/json",
                "User-Agent": AGENTE_DE_USUARIO,
                "Idempotency-Key": idempotencia,
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self._plazo_s) as r:
                return RespuestaHTTP(estado=r.status, cuerpo=r.read())
        except urllib.error.HTTPError as e:
            # Resend contestó con un estado de error. Su cuerpo puede traer el
            # motivo y **no se conserva**: el adaptador sólo necesita el estado.
            return RespuestaHTTP(estado=e.code, motivo="respuesta de error")
        except TimeoutError:
            return RespuestaHTTP(estado=0, motivo="tiempo de espera agotado")
        except urllib.error.URLError:
            # ⚠️ `e.reason` NO se copia: en un fallo de DNS o de TLS trae el
            # anfitrión, y el registro de este módulo no publica destinos.
            return RespuestaHTTP(estado=0, motivo="no se pudo contactar al canal")


def _familia(estado: int) -> str:
    """El estado HTTP en una palabra, para el registro.

    Se normaliza porque lo que hace falta al depurar es la **clase** de fallo
    —«me rechazaron», «se cayó», «no contestó»—; el número exacto va al lado y
    el cuerpo de la respuesta no va nunca.
    """
    if estado == 0:
        return "sin_respuesta"
    if 200 <= estado < 300:
        return "aceptado"
    if 400 <= estado < 500:
        return "rechazado"
    if estado >= 500:
        return "fallo_del_canal"
    return "inesperado"


def _fallo_opaco(clave_idempotencia: str) -> None:
    """Anota que un aviso murió por algo inesperado, **sin decir qué**.

    Tres cosas que este registro NO hace, y las tres son deliberadas:

    - **no publica `str(excepcion)`.** El mensaje de una excepción de red trae
      dentro la URL con sus cabeceras, el anfitrión, y —en un transporte que
      alguien componga mal— la clave de API o el destinatario. Es justo el dato
      que más apetece registrar y el único que este módulo tiene prohibido;
    - **no usa `_LOG.exception()` ni `exc_info`.** Escribirían la traza entera,
      y una traza lleva los argumentos de cada marco: el `carga` con el correo y
      el texto del aviso están ahí dentro;
    - **no publica el tipo de la excepción.** Un `RuntimeError` no dice nada
      útil por sí solo, y el nombre de una clase de excepción puede llevar el
      valor dentro en bibliotecas que las generan (`InvalidKeyError_re_abc…`).

    Lo que sí queda es la clave opaca del aviso, que es lo que permite cruzarlo
    con el trámite. Quien necesite el detalle lo tiene en el panel de Resend o
    reproduciendo el fallo con el transporte a la vista.
    """
    _LOG.error(
        "el aviso [%s] no salió por un fallo inesperado del transporte; "
        "el trámite no se ve afectado",
        clave_idempotencia,
    )


def _identificador_de(cuerpo: bytes) -> str:
    """El `id` que Resend devuelve, o `""` si la respuesta no lo trae.

    Un 2xx sin identificador utilizable no es un envío comprobable: sin él nadie
    puede buscar ese correo en el panel, y llamarlo éxito sería afirmar algo que
    no se puede verificar. Se trata igual que un fallo.
    """
    try:
        datos = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(datos, dict):
        return ""
    identificador = datos.get("id")
    if not isinstance(identificador, str) or not identificador.strip():
        return ""
    return identificador


class AdaptadorResend:
    """`PuertoNotificacion` contra la API HTTP de Resend."""

    def __init__(
        self,
        *,
        remitente: str,
        clave: str = "",
        url: str = URL_DE_ENVIO,
        plazo_s: float = PLAZO_DE_ENVIO_S,
        transporte: TransporteHTTP | None = None,
    ) -> None:
        """`remitente` es obligatorio; la clave sólo si no se inyecta transporte.

        Se comprueba **al construir** y no al primer envío: una composición sin
        remitente es un error de despliegue, y descubrirlo cuando alguien acaba
        de pedir la eliminación de sus datos sería descubrirlo tarde. Quien
        compone (`canal.py`) ya elige `NotificacionRegistrada` antes de llegar
        aquí, así que esta guarda cubre a quien construya el adaptador a mano.
        """
        if not remitente.strip():
            raise ValueError("AdaptadorResend necesita un remitente verificado")
        self._remitente = remitente
        if transporte is not None:
            self._transporte: TransporteHTTP = transporte
            return
        if not clave.strip():
            raise ValueError("AdaptadorResend necesita una clave de envío")
        self._transporte = _TransporteUrllib(url, clave, plazo_s)

    def avisar(
        self,
        correo: str,
        asunto: str,
        cuerpo: str,
        *,
        clave_idempotencia: str,
        html: str = "",
        adjuntos: tuple[dict[str, str], ...] = (),
    ) -> bool:
        """Un `POST`, un correo, ningún reintento. Ver el docstring del módulo.

        La clave de idempotencia viaja en la cabecera que Resend documenta: la
        conserva 24 horas y admite hasta 256 caracteres, de modo que un reintento
        del titular —doble clic, recarga— no le manda dos correos. Las que este
        árbol genera son `<hecho>/<secuencia>`, muy por debajo de ese límite.
        """
        # `to` como lista y no como cadena: es la forma que la API documenta
        # para uno o varios destinatarios, y una sola forma evita que el día que
        # haya dos destinos haya también dos maneras de construir el cuerpo.
        mensaje = {
            "from": self._remitente,
            "to": [correo],
            "subject": asunto,
            "text": cuerpo,
        }
        if html:
            mensaje["html"] = html
        if adjuntos:
            mensaje["attachments"] = [
                {"filename": adjunto["filename"], "content": adjunto["content"]}
                for adjunto in adjuntos
            ]
        carga = json.dumps(mensaje).encode("utf-8")

        try:
            respuesta = self._transporte.enviar(carga, idempotencia=clave_idempotencia)
        except Exception:  # noqa: BLE001 — ver el bloque de abajo
            # ⚠️ **AQUÍ SE CUMPLE «nunca levanta», Y ANTES NO SE CUMPLÍA.**
            #
            # `_TransporteUrllib` traduce los tres fallos que sabe nombrar
            # —`HTTPError`, `TimeoutError`, `URLError`— y por eso parecía que
            # esto sobraba. No sobra: **cualquier otra cosa** que el transporte
            # levante cruzaba hasta el caso de uso, que ya tiene su escritura
            # confirmada. Un `ssl.SSLError` —que no hereda de `URLError`—, un
            # `AttributeError` dentro de `urllib`, un `MemoryError` al leer una
            # respuesta enorme, o un transporte inyectado por otra composición:
            # todos convertían un trámite registrado en un 500. Eso es
            # exactamente el «éxito parcial» que `EQ-024` prohíbe comunicar.
            #
            # El `json.dumps` de arriba queda FUERA del `try` a propósito: sus
            # cuatro campos son cadenas que el caso de uso ya validó, así que un
            # fallo ahí sería un defecto de este módulo y no del canal, y
            # taparlo lo volvería invisible.
            #
            # `Exception` y no `BaseException`: `KeyboardInterrupt`,
            # `SystemExit` y `asyncio.CancelledError` **tienen que seguir
            # subiendo**. Un adaptador de correo que se tragara un Ctrl-C o la
            # cancelación de una tarea impediría apagar el proceso.
            #
            # Y no se reintenta: un fallo inesperado no se arregla repitiéndolo,
            # y el titular está esperando una respuesta que ya está decidida.
            _fallo_opaco(clave_idempotencia)
            return False
        identificador = (
            _identificador_de(respuesta.cuerpo) if 200 <= respuesta.estado < 300 else ""
        )
        salio = bool(identificador)

        # ⚠️ Las cuatro cosas que se registran y ninguna más. Ver el docstring.
        _LOG.info(
            "aviso [%s] %s (http=%s, resend=%s)",
            clave_idempotencia,
            _familia(respuesta.estado),
            respuesta.estado,
            identificador or "-",
        )
        if not salio and respuesta.motivo:
            _LOG.warning("el aviso [%s] no salió: %s", clave_idempotencia, respuesta.motivo)
        elif not salio and 200 <= respuesta.estado < 300:
            _LOG.warning(
                "el aviso [%s] recibió un 2xx sin identificador de Resend", clave_idempotencia
            )
        return salio
