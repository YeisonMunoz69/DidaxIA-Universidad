from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_LOG = logging.getLogger(__name__)


URL_DE_ENVIO = "https://api.resend.com/emails"


AGENTE_DE_USUARIO = "DidaxIa-notificaciones/1.0"


PLAZO_DE_ENVIO_S = 5.0


@dataclass(frozen=True, slots=True)
class RespuestaHTTP:

    estado: int
    cuerpo: bytes = b""
    motivo: str = ""

@runtime_checkable
class TransporteHTTP(Protocol):

    def enviar(self, cuerpo: bytes, *, idempotencia: str) -> RespuestaHTTP:
        ...

class _TransporteUrllib:

    def __init__(self, url: str, clave: str, plazo_s: float) -> None:
        self._url = url
        self._clave = clave
        self._plazo_s = plazo_s

    def enviar(self, cuerpo: bytes, *, idempotencia: str) -> RespuestaHTTP:
        import urllib.error
        import urllib.request

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

            return RespuestaHTTP(estado=e.code, motivo="respuesta de error")
        except TimeoutError:
            return RespuestaHTTP(estado=0, motivo="tiempo de espera agotado")
        except urllib.error.URLError:

            return RespuestaHTTP(estado=0, motivo="no se pudo contactar al canal")

def _familia(estado: int) -> str:
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
    _LOG.error(
        "el aviso [%s] no salió por un fallo inesperado del transporte; "
        "el trámite no se ve afectado",
        clave_idempotencia,
    )

def _identificador_de(cuerpo: bytes) -> str:
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

    def __init__(
        self,
        *,
        remitente: str,
        clave: str = "",
        url: str = URL_DE_ENVIO,
        plazo_s: float = PLAZO_DE_ENVIO_S,
        transporte: TransporteHTTP | None = None,
    ) -> None:

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
        except Exception:

            _fallo_opaco(clave_idempotencia)
            return False
        identificador = (
            _identificador_de(respuesta.cuerpo) if 200 <= respuesta.estado < 300 else ""
        )
        salio = bool(identificador)

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
