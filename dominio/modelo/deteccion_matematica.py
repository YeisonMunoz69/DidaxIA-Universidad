"""
deteccion_matematica.py — Cómo se reconoce matemática en un texto
==================================================================

⚠️ **Este archivo es el punto revisable del contrato.** Está separado a
propósito de `respuesta.py`: la regla **C1** de `ADR-014` —matemática fuera de
referencia invalida la respuesta— **no está en discusión**; *cómo* se reconoce
esa matemática, **sí**. Sustituir esta estrategia no debe tocar C1, C2, C3 ni
C4, ni sus pruebas.

Riesgo registrado: **`R-23`**. Alternativas previstas: `ADR-014` §8.1.

Por qué una lista es tolerable aquí y no lo era en ADR-008
-----------------------------------------------------------
`ADR-008` §1.1 descartó la prosa como interfaz porque **ninguna lista de
patrones cubre todas las formas de enunciar un resultado**. Aquí el problema es
más pequeño: la lista solo tiene que detectar **que hay** matemática, no **cuál
es**. Reconocer un resultado enunciado de cualquier forma es difícil; notar que
aparece un signo de igualdad, no.

Y el fallo cae en distinta dirección. En `ADR-008` una forma no prevista
producía una **aprobación silenciosa**. Aquí produce un rechazo, que es visible.

El sesgo de la lista es deliberado
-----------------------------------
| Error | Qué cuesta |
|---|---|
| **Falso positivo** — marca prosa legítima | Rechaza una respuesta válida. Molesta, **se ve**, se corrige |
| **Falso negativo** — deja pasar matemática | Es lo que el sistema existe para impedir, y **no se ve** |

Por eso la lista se inclina a marcar de más. Lo que **no** hace es marcar una
letra suelta: en español *«el eje x»* es prosa legítima, y una regla que la
marcase produciría rechazos constantes en un sistema cuyo dominio es
matemático.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Marcador:
    """Un indicio de que hay matemática, con el nombre que se registra."""

    patron: re.Pattern
    descripcion: str


#: Estrategia vigente: **marcadores léxicos** (alternativa 1 de `ADR-014` §8.1).
#:
#: Se eligen por no aparecer en prosa española. Cada uno puede retirarse o
#: añadirse sin tocar nada más; las pruebas de `test_contrato_respuesta.py`
#: cubren las dos direcciones —lo que debe marcar y lo que no— de modo que una
#: estrategia nueva se contrasta contra el mismo banco.
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
    # «exponente 2 y al exponente...» usa una conjunción. Mantener la
    # detección de 2y, de 2 y aislado y de 2 y + 3, sin descartar prosa válida.
    Marcador(re.compile(r"\b\d+(?:[a-zA-Z]|\s+(?:[a-xzA-Z]|y(?!\s+(?:al|el|la|los|las|luego|después|se)\b)))\b"), "monomio con variable"),
)


def hallar_matematica(texto: str, marcadores: tuple[Marcador, ...] | None = None) -> list[str]:
    """Devuelve los indicios de matemática hallados en el texto.

    Lista vacía significa que no se encontró ninguno. El parámetro
    ``marcadores`` existe para poder contrastar estrategias sin modificar el
    módulo, que es la condición de que `R-23` sea barato de resolver.
    """
    conjunto = MARCADORES if marcadores is None else marcadores
    hallados = []
    for m in conjunto:
        encontrado = m.patron.search(texto)
        if encontrado:
            hallados.append(f"{m.descripcion} «{encontrado.group(0).strip()}»")
    return hallados
