"""Descarga acotada de la foto firmada en el perfil de Google Workspace."""

from __future__ import annotations

import urllib.request
from urllib.parse import urlparse

from adaptadores.salientes.almacenamiento.fotos_perfil import LIMITE_ENTRADA_BYTES

_HOSTS = {"lh3.googleusercontent.com", "googleusercontent.com"}


def descargar_foto_google(url: str) -> bytes | None:
    """Bytes de un host de imágenes de Google o ``None``; nunca sigue hosts ajenos."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host in _HOSTS or host.endswith(".googleusercontent.com")):
            return None
        peticion = urllib.request.Request(
            url, headers={"User-Agent": "DidaxIa-perfil/1.0", "Accept": "image/*"}
        )
        with urllib.request.urlopen(peticion, timeout=3) as respuesta:  # noqa: S310
            tipo = (respuesta.headers.get_content_type() or "").lower()
            if not tipo.startswith("image/"):
                return None
            cuerpo = respuesta.read(LIMITE_ENTRADA_BYTES + 1)
            return cuerpo if len(cuerpo) <= LIMITE_ENTRADA_BYTES else None
    except (OSError, ValueError):
        return None
