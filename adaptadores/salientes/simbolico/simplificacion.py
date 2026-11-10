"""
simplificacion.py — Forma canónica compacta de un resultado
===============================================================

`pasos.py` conserva primero la derivada sin reducir para poder explicar la
regla aplicada en cada paso; este módulo genera después una forma legible
para el resultado final y para la comparación de `verificar()`. Adaptado sin
cambios de comportamiento desde `sympy_simplify.py` (49 líneas de origen) —
es el único de los archivos traídos que ya cumplía las normas de esta sesión
tal cual estaba.

Por qué no basta `sympy.simplify()` a secas
----------------------------------------------
Puede ser costoso, y puede convertir una expresión clara en una identidad
trigonométrica menos pedagógica. Se combinan varias transformaciones baratas
—agrupar fracciones, cancelar factores, factorizar términos— y se elige la
de menor complejidad, no la primera que SymPy proponga.
"""

from __future__ import annotations

import contextlib

import sympy as sp


def _profundidad_de_fraccion(expr: sp.Expr) -> int:
    """Cuenta fracciones anidadas, para preferir formas menos anidadas."""
    numerador, denominador = sp.fraction(expr)
    if denominador != 1:
        return 1 + _profundidad_de_fraccion(numerador)
    return max((_profundidad_de_fraccion(a) for a in expr.args), default=0)


def _complejidad(expr: sp.Expr) -> tuple[int, int, int, int]:
    """Ordena candidatos: menos fracciones anidadas, menos operaciones, más corto."""
    try:
        operaciones = int(sp.count_ops(expr, visual=False))
    except Exception:                                                # noqa: BLE001
        operaciones = 10**9
    texto = str(expr)
    return _profundidad_de_fraccion(expr), operaciones, len(texto), len(sp.latex(expr))


def simplificar(expr: sp.Expr) -> sp.Expr:
    """Devuelve una forma algebraicamente equivalente y razonablemente mínima."""
    if not isinstance(expr, sp.Expr):
        return expr

    candidatos: list[sp.Expr] = [expr]
    numero_de_operaciones = _complejidad(expr)[1]

    with contextlib.suppress(Exception):
        junta = sp.together(expr, deep=True)
        candidatos.append(junta)
        candidatos.append(sp.cancel(junta))

    with contextlib.suppress(Exception):
        candidatos.append(sp.factor_terms(expr))

    # Factorizar expresiones grandes puede ser muy costoso: se reserva a las
    # que ya tienen pocas operaciones, para no comprometer RNF-EFI-01.
    if numero_de_operaciones <= 250:
        with contextlib.suppress(Exception):
            candidatos.append(sp.factor(expr))

    with contextlib.suppress(Exception):
        candidatos.append(sp.powsimp(expr, force=False, combine="all"))

    # sin(x + pi/4) es equivalente pero menos legible para Cálculo 1 cuando
    # aparece junto a una exponencial: se evita esa transformación ahí.
    if expr.has(sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot) and not expr.has(sp.exp):
        with contextlib.suppress(Exception):
            trig = sp.trigsimp(expr)
            if not (trig.has(sp.pi) and not expr.has(sp.pi)):
                candidatos.append(trig)

    return min(candidatos, key=_complejidad)
