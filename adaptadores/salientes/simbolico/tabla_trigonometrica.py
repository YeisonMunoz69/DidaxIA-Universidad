"""
tabla_trigonometrica.py — Reglas de derivación de funciones trascendentes
============================================================================

Extraído de `pasos.py` para que ningún archivo pase de 400 líneas —el propio
`sympy_steps.py` de origen tenía esta tabla mezclada con el motor de pasos en
un único método de 300 líneas, que las normas de esta sesión no permiten
copiar tal cual.

Cada entrada es `clase_sympy -> (constructor_de_la_derivada, nombre_de_la_
regla, plantilla_latex)`. `pasos.py` la recorre para reconocer qué regla
aplica al nodo que está derivando; el constructor recibe el argumento interno
de la función y devuelve el nodo derivado, sin resolver la regla de la cadena
—eso lo hace `pasos.py` al seguir derivando ese argumento.
"""

from __future__ import annotations

from collections.abc import Callable

import sympy as sp
from sympy import Derivative, Symbol

Constructor = Callable[[sp.Expr], sp.Expr]
Entrada = tuple[Constructor, str, str]


def reglas(x: Symbol, v: str) -> dict[type, Entrada]:
    """La tabla, construida para la variable `x` (de nombre `v`) de este turno."""
    return {
        # ── Trigonométricas ──────────────────────────────────────────────
        sp.sin: (
            lambda a: sp.cos(a) * Derivative(a, x),
            "Derivada del Seno",
            rf"\dfrac{{d}}{{d{v}}}[\sin u] = \cos u \cdot u'",
        ),
        sp.cos: (
            lambda a: -sp.sin(a) * Derivative(a, x),
            "Derivada del Coseno",
            rf"\dfrac{{d}}{{d{v}}}[\cos u] = -\sin u \cdot u'",
        ),
        sp.tan: (
            lambda a: sp.sec(a) ** 2 * Derivative(a, x),
            "Derivada de la Tangente",
            rf"\dfrac{{d}}{{d{v}}}[\tan u] = \sec^2 u \cdot u'",
        ),
        sp.cot: (
            lambda a: -sp.csc(a) ** 2 * Derivative(a, x),
            "Derivada de la Cotangente",
            rf"\dfrac{{d}}{{d{v}}}[\cot u] = -\csc^2 u \cdot u'",
        ),
        sp.sec: (
            lambda a: sp.sec(a) * sp.tan(a) * Derivative(a, x),
            "Derivada de la Secante",
            rf"\dfrac{{d}}{{d{v}}}[\sec u] = \sec u \cdot \tan u \cdot u'",
        ),
        sp.csc: (
            lambda a: -sp.csc(a) * sp.cot(a) * Derivative(a, x),
            "Derivada de la Cosecante",
            rf"\dfrac{{d}}{{d{v}}}[\csc u] = -\csc u \cdot \cot u \cdot u'",
        ),
        # ── Inversas ──────────────────────────────────────────────────────
        sp.asin: (
            lambda a: Derivative(a, x) / sp.sqrt(1 - a ** 2),
            "Derivada del Arcoseno",
            rf"\dfrac{{d}}{{d{v}}}[\arcsin u] = \dfrac{{u'}}{{\sqrt{{1-u^2}}}}",
        ),
        sp.acos: (
            lambda a: -Derivative(a, x) / sp.sqrt(1 - a ** 2),
            "Derivada del Arcocoseno",
            rf"\dfrac{{d}}{{d{v}}}[\arccos u] = \dfrac{{-u'}}{{\sqrt{{1-u^2}}}}",
        ),
        sp.atan: (
            lambda a: Derivative(a, x) / (1 + a ** 2),
            "Derivada de la Arcotangente",
            rf"\dfrac{{d}}{{d{v}}}[\arctan u] = \dfrac{{u'}}{{1+u^2}}",
        ),
        sp.acot: (
            lambda a: -Derivative(a, x) / (1 + a ** 2),
            "Derivada de la Arcocotangente",
            rf"\dfrac{{d}}{{d{v}}}[\text{{arccot}}\,u] = \dfrac{{-u'}}{{1+u^2}}",
        ),
        sp.asec: (
            lambda a: Derivative(a, x) / (sp.Abs(a) * sp.sqrt(a ** 2 - 1)),
            "Derivada del Arcosecante",
            rf"\dfrac{{d}}{{d{v}}}[\text{{arcsec}}\,u] = \dfrac{{u'}}{{|u|\sqrt{{u^2-1}}}}",
        ),
        sp.acsc: (
            lambda a: -Derivative(a, x) / (sp.Abs(a) * sp.sqrt(a ** 2 - 1)),
            "Derivada del Arcocosecante",
            rf"\dfrac{{d}}{{d{v}}}[\text{{arccsc}}\,u] = \dfrac{{-u'}}{{|u|\sqrt{{u^2-1}}}}",
        ),
        # ── Hiperbólicas ──────────────────────────────────────────────────
        sp.sinh: (
            lambda a: sp.cosh(a) * Derivative(a, x),
            "Derivada del Seno Hiperbólico",
            rf"\dfrac{{d}}{{d{v}}}[\sinh u] = \cosh u \cdot u'",
        ),
        sp.cosh: (
            lambda a: sp.sinh(a) * Derivative(a, x),
            "Derivada del Coseno Hiperbólico",
            rf"\dfrac{{d}}{{d{v}}}[\cosh u] = \sinh u \cdot u'",
        ),
        sp.tanh: (
            lambda a: (1 - sp.tanh(a) ** 2) * Derivative(a, x),
            "Derivada de la Tangente Hiperbólica",
            rf"\dfrac{{d}}{{d{v}}}[\tanh u] = (1-\tanh^2 u) \cdot u'",
        ),
        sp.coth: (
            lambda a: -(sp.Integer(1) / sp.sinh(a) ** 2) * Derivative(a, x),
            "Derivada de la Cotangente Hiperbólica",
            rf"\dfrac{{d}}{{d{v}}}[\coth u] = -\text{{csch}}^2 u \cdot u'",
        ),
    }
