from __future__ import annotations

from typing import Any


PLAZO_DE_CONEXION_S = 5


def conectar(cadena: str) -> Any:
    import psycopg

    return psycopg.connect(cadena, connect_timeout=PLAZO_DE_CONEXION_S)
