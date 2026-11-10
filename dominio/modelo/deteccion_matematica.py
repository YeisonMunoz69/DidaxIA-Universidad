from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Marcador:

    patron: re.Pattern
    descripcion: str

MARCADORES: tuple[Marcador, ...] = (
    Marcador(re.compile(r"[=≠≤≥<>]"), "signo de relación"),
    Marcador(
        re.compile(r"\\(?:d?frac|sqrt|int|sum|lim|cdot|left|right|begin)\b"),
        "orden de LaTeX",
    ),
    Marcador(re.compile(r"\$|\\\(|\\\[|\\\)|\\\]"), "delimitador de LaTeX"),
    Marcador(re.compile(r"\^\s*\{?\s*[-\d]"), "exponente"),
    Marcador(
        re.compile(r"\b(?:sin|sen|cos|tan|tg|log|ln|exp|sqrt|raiz)\s*\("),
        "llamada a función",
    ),
    Marcador(re.compile(r"\b\d+\s*[*/]\s*[a-zA-Z]"), "producto o cociente con variable"),
    Marcador(re.compile(r"\b\d+\s*[a-zA-Z]\s*\^"), "monomio con exponente"),

    Marcador(re.compile(r"\b\d+(?:[a-zA-Z]|\s+(?:[a-xzA-Z]|y(?!\s+(?:al|el|la|los|las|luego|después|se)\b)))\b"), "monomio con variable"),
)


def hallar_matematica(texto: str, marcadores: tuple[Marcador, ...] | None = None) -> list[str]:
    conjunto = MARCADORES if marcadores is None else marcadores
    hallados = []
    for m in conjunto:
        encontrado = m.patron.search(texto)
        if encontrado:
            hallados.append(f"{m.descripcion} «{encontrado.group(0).strip()}»")
    return hallados
