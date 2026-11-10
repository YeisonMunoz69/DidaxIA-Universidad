from __future__ import annotations

import os
from typing import Any


VARIABLE_ENTORNO = "AGENTE_ENTORNO"


ENTORNOS_SIN_TLS = frozenset(
    {"desarrollo", "local", "pruebas", "demostracion", "produccion-local"}
)


DURACION_SEGUNDOS = 7 * 24 * 60 * 60


def entorno_sin_tls(entorno: str | None = None) -> bool:
    valor = (os.environ.get(VARIABLE_ENTORNO, "") if entorno is None else entorno)
    return valor.strip().lower() in ENTORNOS_SIN_TLS

def atributos(entorno: str | None = None) -> dict[str, Any]:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": not entorno_sin_tls(entorno),
        "path": "/",
    }

def atributos_de_borrado(entorno: str | None = None) -> dict[str, Any]:
    return atributos(entorno)
