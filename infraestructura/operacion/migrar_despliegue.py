"""Aplica las migraciones únicamente a la base interna del despliegue Compose."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from urllib.parse import urlsplit

from adaptadores.salientes.conexion import conectar
from infraestructura.migraciones.catalogo import CatalogoInvalido
from infraestructura.migraciones.ejecutor import ErrorDeMigracion, ejecutar


class DespliegueNoAutorizado(RuntimeError):
    """La configuración no identifica inequívocamente la base interna."""


def cadena_interna_autorizada(entorno: Mapping[str, str] | None = None) -> str:
    """Devuelve ``AGENTE_BD`` sólo para ``base:5432/agente`` en producción."""
    valores = os.environ if entorno is None else entorno
    if valores.get("AGENTE_ENTORNO", "").strip().lower() != "produccion":
        raise DespliegueNoAutorizado("AGENTE_ENTORNO debe ser 'produccion'")
    if valores.get("AGENTE_MIGRACION_AUTORIZADA", "").strip() != "1":
        raise DespliegueNoAutorizado("falta AGENTE_MIGRACION_AUTORIZADA=1")

    cadena = valores.get("AGENTE_BD", "").strip()
    if not cadena:
        raise DespliegueNoAutorizado("falta AGENTE_BD")
    try:
        partes = urlsplit(cadena)
        puerto = partes.port
    except ValueError:
        raise DespliegueNoAutorizado("AGENTE_BD no es una URL válida") from None

    if partes.scheme.lower() not in {"postgres", "postgresql"}:
        raise DespliegueNoAutorizado("AGENTE_BD debe usar postgresql://")
    if (partes.hostname or "").lower() != "base" or (puerto or 5432) != 5432:
        raise DespliegueNoAutorizado("sólo se admite PostgreSQL interno en base:5432")
    if partes.path.lstrip("/").lower() != "agente":
        raise DespliegueNoAutorizado("la base debe llamarse exactamente 'agente'")
    if partes.username != "agente":
        raise DespliegueNoAutorizado("el usuario debe llamarse exactamente 'agente'")
    return cadena


def main() -> int:
    try:
        cadena = cadena_interna_autorizada()
        with conectar(cadena) as conexion:
            resultado = ejecutar(conexion)
    except (DespliegueNoAutorizado, CatalogoInvalido, ErrorDeMigracion) as exc:
        print(f"Migración de despliegue detenida · {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # la conexión también debe impedir el arranque
        print(f"Migración de despliegue fallida · {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(
        "Migraciones de despliegue correctas · "
        f"adoptadas={list(resultado.adoptadas)} aplicadas={list(resultado.aplicadas)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
