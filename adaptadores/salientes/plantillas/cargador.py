from __future__ import annotations

import re
from pathlib import Path

from adaptadores.salientes.plantillas.items import items_desde_texto
from dominio.puertos.plantillas import (
    AUTOCONCEPTO,
    AUTORREGULACION,
    SCAFFOLDING_KQ,
    SOCRATICA_APOS,
    TWO_TIER,
    ItemDosNiveles,
    Plantilla,
)


_ARCHIVO_DE_CLAVE = {
    SOCRATICA_APOS: "p-socratica-apos.md",
    SCAFFOLDING_KQ: "p-scaffolding-kq1-kq5.md",
    TWO_TIER: "p-two-tier.md",
    AUTOCONCEPTO: "p-retroalimentacion-autoconcepto.md",
    AUTORREGULACION: "p-autorregulacion.md",
}


MARCA_INICIO = "<!-- repertorio: inicio -->"
MARCA_FIN = "<!-- repertorio: fin -->"


_PREGUNTA = re.compile(r"(?:\*\*|\*|__|_)«([^»]+)»(?:\*\*|\*|__|_)")


_FILA = "|"
_CITA = ">"


_TITULO = re.compile(r"^#\s+(.+)$", re.M)


_SECUENCIA = re.compile(r"^s-(m\d{2})\.md$", re.I)


class CargadorDePlantillas:

    def __init__(self, directorio: Path) -> None:
        self._por_concepcion: dict[str, Plantilla] = {}
        self._por_clave: dict[str, Plantilla] = {}

        self._problemas: list[str] = []

        self._items_por_nodo: dict[str, ItemDosNiveles] = {}
        self._cargar(directorio)

    def _cargar(self, directorio: Path) -> None:
        if not directorio.is_dir():

            return
        for archivo in sorted(directorio.glob("*.md")):
            texto = _leer(archivo)
            if texto is None:
                self._problemas.append(f"{archivo.name}: no se pudo leer")
                continue
            secuencia = _SECUENCIA.match(archivo.name)
            if secuencia is not None:
                concepcion = secuencia.group(1).upper()
                self._por_concepcion[concepcion] = self._plantilla(
                    concepcion, texto, archivo.name
                )
                continue
            for clave, nombre in _ARCHIVO_DE_CLAVE.items():
                if archivo.name == nombre:
                    self._por_clave[clave] = self._plantilla(clave, texto, archivo.name)
                    if clave == TWO_TIER:

                        for item in items_desde_texto(texto):
                            self._items_por_nodo[item.nodo] = item
                    break

    def _plantilla(self, clave: str, texto: str, archivo: str) -> Plantilla:
        titulo = _TITULO.search(texto)
        preguntas, problema = repertorio(texto)
        if problema:
            self._problemas.append(f"{archivo}: {problema}")
        return Plantilla(
            clave=clave,
            titulo=titulo.group(1).strip() if titulo else clave,
            preguntas=preguntas,
            diagnostico=problema,
        )

    def secuencia_de(self, concepcion: str) -> Plantilla | None:
        return self._por_concepcion.get(concepcion.strip().upper())

    def plantilla(self, clave: str) -> Plantilla | None:
        return self._por_clave.get(clave)

    def item_de(self, nodo: str) -> ItemDosNiveles | None:
        return self._items_por_nodo.get(nodo.strip().upper())

    def nodo_del_ejercicio(self, expresion: str) -> str | None:
        from dominio.pedagogia.problema import (
            normalizar_expresion,
        )

        clave = normalizar_expresion(expresion)
        if not clave:
            return None
        for nodo, item in self._items_por_nodo.items():
            if item.derivar and normalizar_expresion(item.derivar) == clave:
                return nodo
        return None

    @property
    def cuantas(self) -> tuple[int, int]:
        return len(self._por_concepcion), len(self._por_clave)

    @property
    def problemas(self) -> tuple[str, ...]:
        return tuple(self._problemas)

def _leer(archivo: Path) -> str | None:
    try:
        return archivo.read_text(encoding="utf-8")
    except OSError:
        return None

def _regiones(lineas: list[str]) -> tuple[list[list[str]], str]:
    regiones: list[list[str]] = []
    dentro = False
    actual: list[str] = []
    for numero, linea in enumerate(lineas, start=1):
        plano = linea.strip()
        if plano == MARCA_INICIO:
            if dentro:
                return [], f"«repertorio: inicio» anidado en la línea {numero}"
            dentro = True
            actual = []
            continue
        if plano == MARCA_FIN:
            if not dentro:
                return [], f"«repertorio: fin» sin apertura en la línea {numero}"
            regiones.append(actual)
            dentro = False
            continue
        if dentro:
            actual.append(linea)
    if dentro:
        return [], "«repertorio: inicio» sin su «repertorio: fin»"
    if not regiones:
        return [], "sin delimitación de repertorio"
    return regiones, ""

def _unidades(region: list[str]) -> list[str]:
    unidades: list[str] = []
    cita: list[str] = []
    for linea in region:
        pelada = linea.lstrip()
        if pelada.startswith(_CITA):
            cita.append(pelada.lstrip(">").strip())
            continue
        if cita:
            unidades.append(" ".join(cita))
            cita = []
        if pelada.startswith(_FILA):
            unidades.append(pelada)
    if cita:
        unidades.append(" ".join(cita))
    return unidades

def repertorio(texto: str) -> tuple[tuple[str, ...], str]:
    regiones, problema = _regiones(texto.splitlines())
    if problema:
        return (), problema

    salida: list[str] = []
    for region in regiones:
        for unidad in _unidades(region):
            for cruda in _PREGUNTA.findall(unidad):

                limpia = " ".join(cruda.split())
                if limpia:
                    salida.append(limpia)
    if not salida:
        return (), "el repertorio delimitado no contiene ninguna cita enfatizada"
    return tuple(salida), ""
