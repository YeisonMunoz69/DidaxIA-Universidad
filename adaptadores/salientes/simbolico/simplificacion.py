from __future__ import annotations

import contextlib

import sympy as sp


def _profundidad_de_fraccion(expr: sp.Expr) -> int:
    numerador, denominador = sp.fraction(expr)
    if denominador != 1:
        return 1 + _profundidad_de_fraccion(numerador)
    return max((_profundidad_de_fraccion(a) for a in expr.args), default=0)

def _complejidad(expr: sp.Expr) -> tuple[int, int, int, int]:
    try:
        operaciones = int(sp.count_ops(expr, visual=False))
    except Exception:
        operaciones = 10**9
    texto = str(expr)
    return _profundidad_de_fraccion(expr), operaciones, len(texto), len(sp.latex(expr))

def simplificar(expr: sp.Expr) -> sp.Expr:
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

    if numero_de_operaciones <= 250:
        with contextlib.suppress(Exception):
            candidatos.append(sp.factor(expr))

    with contextlib.suppress(Exception):
        candidatos.append(sp.powsimp(expr, force=False, combine="all"))

    if expr.has(sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot) and not expr.has(sp.exp):
        with contextlib.suppress(Exception):
            trig = sp.trigsimp(expr)
            if not (trig.has(sp.pi) and not expr.has(sp.pi)):
                candidatos.append(trig)

    return min(candidatos, key=_complejidad)
