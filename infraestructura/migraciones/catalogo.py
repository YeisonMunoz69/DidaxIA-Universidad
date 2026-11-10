"""Descubrimiento inmutable de los SQL numerados que forman la línea base."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

PATRON_NOMBRE = re.compile(r"^(?P<version>\d{2})-(?P<nombre>[a-z0-9-]+)\.sql$")
CONTROL_TRANSACCION = {"BEGIN;", "COMMIT;"}


class CatalogoInvalido(RuntimeError):
    """Los archivos no forman una secuencia segura y determinista."""


@dataclass(frozen=True, slots=True)
class Migracion:
    version: int
    nombre: str
    ruta: Path
    checksum: str
    sql: str


def directorio_predeterminado() -> Path:
    return Path(__file__).resolve().parents[1] / "esquema"


def _sql_ejecutable(contenido: str, archivo: str) -> str:
    lineas = contenido.splitlines()
    if lineas and lineas[0].startswith("\ufeff"):
        lineas[0] = lineas[0].lstrip("\ufeff")

    metacomandos = [linea for linea in lineas if linea.lstrip().startswith("\\")]
    if metacomandos:
        if lineas[0].strip().lower() != "\\encoding utf8" or len(metacomandos) != 1:
            raise CatalogoInvalido(
                f"{archivo}: sólo se admite \\encoding UTF8 como primera línea"
            )
        lineas = lineas[1:]

    # El ejecutor gobierna una única transacción para SQL + ledger. Los BEGIN
    # y COMMIT históricos, aislados en su propia línea, no pueden cerrarla antes.
    lineas = [linea for linea in lineas if linea.strip().upper() not in CONTROL_TRANSACCION]
    sql = "\n".join(lineas).strip()
    if not sql:
        raise CatalogoInvalido(f"{archivo}: la migración quedó vacía")
    return sql


def descubrir(directorio: Path | None = None) -> tuple[Migracion, ...]:
    raiz = directorio_predeterminado() if directorio is None else Path(directorio)
    rutas = sorted(raiz.glob("*.sql"))
    if not rutas:
        raise CatalogoInvalido(f"no hay migraciones SQL en {raiz}")

    migraciones: list[Migracion] = []
    for posicion, ruta in enumerate(rutas, start=1):
        coincidencia = PATRON_NOMBRE.fullmatch(ruta.name)
        if not coincidencia:
            raise CatalogoInvalido(f"nombre de migración no válido: {ruta.name}")
        version = int(coincidencia.group("version"))
        if version != posicion:
            raise CatalogoInvalido(
                f"se esperaba la versión {posicion:02d} y apareció {ruta.name}"
            )
        bruto = ruta.read_bytes()
        try:
            contenido = bruto.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CatalogoInvalido(f"{ruta.name}: no está codificado en UTF-8") from exc
        migraciones.append(
            Migracion(
                version=version,
                nombre=coincidencia.group("nombre"),
                ruta=ruta,
                checksum=hashlib.sha256(bruto).hexdigest(),
                sql=_sql_ejecutable(contenido, ruta.name),
            )
        )
    return tuple(migraciones)
