from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from google.auth.transport import requests as _google_transporte
from google.oauth2 import id_token as _google_id_token

_registro = logging.getLogger(__name__)


_DESFASE_RELOJ_SEGUNDOS = 60


def _motivo_de_verificacion(error: Exception) -> str:
    texto = str(error).casefold()
    if "audience" in texto:
        return "audiencia"
    if "expired" in texto:
        return "expirado"
    if "too early" in texto or "issued at" in texto:
        return "reloj_adelantado"
    if "signature" in texto or "certificate" in texto or "signing key" in texto:
        return "firma"
    if "issuer" in texto:
        return "emisor"
    return "otro"

DOMINIO_INSTITUCIONAL = os.environ.get("DOMINIO_INSTITUCIONAL", "unimayor.edu.co")


_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


@dataclass(frozen=True)
class IdentidadVerificada:

    identificador: str
    correo: str
    nombre: str

    emitido_en: datetime | None

    autenticado_en: datetime | None = None
    foto_url: str = ""

def esta_configurado() -> bool:
    return bool(_CLIENT_ID)

def verificar_id_token(id_token_recibido: str) -> IdentidadVerificada | None:
    if not id_token_recibido:
        _registro.warning("identidad_google_rechazada motivo=token_ausente")
        return None
    if not _CLIENT_ID:
        _registro.warning("identidad_google_rechazada motivo=cliente_no_configurado")
        return None
    try:
        claims = _google_id_token.verify_oauth2_token(
            id_token_recibido,
            _google_transporte.Request(),
            _CLIENT_ID,
            clock_skew_in_seconds=_DESFASE_RELOJ_SEGUNDOS,
        )
    except Exception as error:

        _registro.warning(
            "identidad_google_rechazada motivo=verificacion categoria=%s clase=%s",
            _motivo_de_verificacion(error),
            type(error).__name__,
        )
        return None

    if claims.get("hd") != DOMINIO_INSTITUCIONAL:
        _registro.warning("identidad_google_rechazada motivo=dominio_institucional")
        return None
    identificador = claims.get("sub")
    correo = claims.get("email")
    if not identificador or not correo:
        _registro.warning("identidad_google_rechazada motivo=claims_incompletos")
        return None
    return IdentidadVerificada(
        identificador=str(identificador),
        correo=str(correo).strip().lower(),
        nombre=str(claims.get("name") or ""),

        emitido_en=_momento_del_claim(claims.get("iat")),
        autenticado_en=_momento_del_claim(claims.get("auth_time")),
        foto_url=str(claims.get("picture") or ""),
    )

def _momento_del_claim(valor: object) -> datetime | None:
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto.isdigit():
            return None
        valor = int(texto)
    if not isinstance(valor, int | float):
        return None
    try:
        return datetime.fromtimestamp(float(valor), tz=UTC)
    except (OSError, OverflowError, ValueError):

        return None
