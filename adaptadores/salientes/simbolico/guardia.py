"""
guardia.py — Frontera léxica previa al análisis
===============================================

Primera de las tres capas de defensa que `ADR-011` §5.3 declara. Es puramente
léxica y **no depende de la versión de SymPy**, que es justo lo que le faltaba
al artefacto previo: allí la frontera descansaba en detalles internos del
analizador, y se comprobó que `().__class__.__bases__` se resolvía sin error.

Las tres capas son independientes a propósito. Ninguna presupone que las otras
funcionen — misma lógica con la que `ADR-008` invirtió el veredicto por defecto.
"""

from __future__ import annotations

import os
import re


class EntradaNoAdmitida(ValueError):
    """La entrada contiene construcciones que este sistema no acepta."""


def _entero(nombre: str, defecto: int) -> int:
    """Umbral configurable sin recompilar (`RF-ADM-06` · `RI-13`)."""
    try:
        return int(os.environ.get(nombre, "") or defecto)
    except ValueError:
        return defecto


MAX_CARACTERES = _entero("AGENTE_MAX_EXPRESION", 500)

_DUNDER = re.compile(r"__")
_ATRIBUTO = re.compile(r"\.\s*[A-Za-z_]")          # el punto decimal va seguido de dígito
_SIMBOLOS = re.compile(r"[\[\]{};:@\\`\"']")
_PALABRAS = re.compile(
    r"\b(import|lambda|for|while|class|def|global|exec|eval|open|getattr|setattr|"
    r"delattr|vars|dir|globals|locals|compile|input|breakpoint|subclasses|mro)\b"
)


def exigir_entrada_admisible(texto: str) -> str:
    """Valida la entrada y la devuelve sin modificar si es admisible."""
    if texto is None or not str(texto).strip():
        raise EntradaNoAdmitida("la expresión está vacía")

    valor = str(texto)

    if len(valor) > MAX_CARACTERES:
        raise EntradaNoAdmitida(
            f"la expresión excede el máximo de {MAX_CARACTERES} caracteres"
        )
    if _DUNDER.search(valor):
        raise EntradaNoAdmitida("contiene atributos especiales del lenguaje")
    if _ATRIBUTO.search(valor):
        raise EntradaNoAdmitida(
            "contiene acceso por atributo; el punto solo se admite como separador decimal"
        )
    if _SIMBOLOS.search(valor):
        raise EntradaNoAdmitida("contiene caracteres que la notación matemática no usa")
    if _PALABRAS.search(valor):
        raise EntradaNoAdmitida("contiene palabras reservadas del lenguaje")

    return valor
