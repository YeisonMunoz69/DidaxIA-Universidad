from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dominio.modelo.consentimiento import Alcance, ConsentimientoInvalido, Finalidad
from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)


FORMATO = 1


class ManifiestoInvalido(RuntimeError):
    pass

def _texto(entrada: dict, campo: str, posicion: int) -> str:
    valor = entrada.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ManifiestoInvalido(f"versión #{posicion}: falta «{campo}» o está vacío")
    return valor.strip()

def _momento(entrada: dict, campo: str, posicion: int, *, obligatorio: bool) -> datetime | None:
    crudo = entrada.get(campo)
    if crudo is None:
        if obligatorio:
            raise ManifiestoInvalido(f"versión #{posicion}: falta «{campo}»")
        return None
    if not isinstance(crudo, str):
        raise ManifiestoInvalido(f"versión #{posicion}: «{campo}» tiene que ser texto ISO-8601")
    try:
        momento = datetime.fromisoformat(crudo)
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «{campo}» no es una fecha ISO-8601"
        ) from exc
    if momento.tzinfo is None:

        raise ManifiestoInvalido(
            f"versión #{posicion}: «{campo}» tiene que declarar zona horaria"
        )
    return momento

def _ruta_dentro(carpeta: Path, nombre: str, posicion: int) -> Path:
    raiz = carpeta.resolve()
    candidata = (raiz / nombre).resolve()
    try:
        dentro = os.path.commonpath([str(candidata), str(raiz)]) == str(raiz)
    except ValueError:
        dentro = False
    if not dentro:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «archivo» apunta fuera de la carpeta de textos"
        )
    if not candidata.is_file():
        raise ManifiestoInvalido(
            f"versión #{posicion}: no existe el archivo declarado en «archivo»"
        )
    return candidata

def _alcance_de(entrada: dict, posicion: int) -> Alcance:
    try:
        return Alcance(_texto(entrada, "alcance", posicion))
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «alcance» no es uno de "
            f"{', '.join(a.value for a in Alcance)}"
        ) from exc

def _finalidades_de(entrada: dict, posicion: int) -> frozenset[Finalidad]:
    crudas = entrada.get("finalidades")
    if not isinstance(crudas, list) or not crudas:
        raise ManifiestoInvalido(f"versión #{posicion}: «finalidades» no puede faltar")
    try:
        return frozenset(Finalidad(f) for f in crudas)
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: hay una finalidad que no es del catálogo cerrado"
        ) from exc

def _cuerpo_de(entrada: dict, textos: Path, posicion: int) -> str:
    ruta = _ruta_dentro(Path(textos), _texto(entrada, "archivo", posicion), posicion)
    try:
        return ruta.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: el archivo no se pudo leer como UTF-8"
        ) from exc

def _publicacion_de(entrada: dict, textos: Path, posicion: int) -> PublicacionDeVersion:
    if not isinstance(entrada, dict):
        raise ManifiestoInvalido(f"versión #{posicion}: cada versión es un objeto")
    try:
        return PublicacionDeVersion(
            instantanea=InstantaneaDeVersion(
                codigo=_texto(entrada, "codigo", posicion),
                alcance=_alcance_de(entrada, posicion),
                cuerpo=_cuerpo_de(entrada, textos, posicion),
            ),
            finalidades=_finalidades_de(entrada, posicion),
            vigente_desde=_momento(entrada, "vigente_desde", posicion, obligatorio=True),
            vigente_hasta=_momento(entrada, "vigente_hasta", posicion, obligatorio=False),
        )
    except ConsentimientoInvalido as exc:

        raise ManifiestoInvalido(f"versión #{posicion}: {exc}") from exc

def _entradas_del(manifiesto: Path) -> list:
    if not manifiesto.is_file():
        raise ManifiestoInvalido("no existe el manifiesto")
    try:
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifiestoInvalido("el manifiesto no es JSON válido") from exc
    if not isinstance(datos, dict):
        raise ManifiestoInvalido("el manifiesto tiene que ser un objeto JSON")
    if datos.get("formato") != FORMATO:
        raise ManifiestoInvalido(
            f"formato de manifiesto desconocido; esta herramienta lee el {FORMATO}"
        )
    crudas = datos.get("versiones")
    if not isinstance(crudas, list) or not crudas:
        raise ManifiestoInvalido("el manifiesto no declara ninguna versión")
    return crudas

def leer(manifiesto: Path, textos: Path) -> tuple[PublicacionDeVersion, ...]:
    if not Path(textos).is_dir():
        raise ManifiestoInvalido("la carpeta de textos no existe o no es un directorio")

    publicaciones: list[PublicacionDeVersion] = []
    vistos: set[str] = set()
    for posicion, entrada in enumerate(_entradas_del(Path(manifiesto)), start=1):
        publicacion = _publicacion_de(entrada, Path(textos), posicion)
        if publicacion.codigo in vistos:

            raise ManifiestoInvalido(f"el código «{publicacion.codigo}» aparece dos veces")
        vistos.add(publicacion.codigo)
        publicaciones.append(publicacion)

    return tuple(publicaciones)
