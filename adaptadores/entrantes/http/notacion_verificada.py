from __future__ import annotations

import re

import sympy as sp
from sympy.printing.latex import LatexPrinter

from adaptadores.salientes.simbolico.analizador import analizar

_LIMITE = re.compile(
    r"^lim\s+(?P<variable>[a-zA-Z])->(?P<destino>[^\s()]+)\s*\((?P<expresion>.*)\)$",
    re.S,
)
_DERIVADA = re.compile(
    r"^d/d(?P<variable>[a-zA-Z])\s*\((?P<expresion>.*)\)$", re.S,
)


class _NotacionDeRegla(LatexPrinter):
    def _print_Derivative(self, expr):
        funcion = expr.expr
        if (len(expr.variables) == 1 and str(funcion.func) in ('f', 'g', 'u', 'v')
                and funcion.args == (expr.variables[0],)):
            return rf"{funcion.func}'\left({self._print(funcion.args[0])}\right)"
        return super()._print_Derivative(expr)

    def _print_Subs(self, expr):
        if (len(expr.variables) == 1 and isinstance(expr.expr, sp.Derivative)
                and expr.expr.variables == expr.variables
                and str(expr.expr.expr.func) in ('f', 'g', 'u', 'v')
                and expr.expr.expr.args == expr.variables):
            return rf"{expr.expr.expr.func}'\left({self._print(expr.point[0])}\right)"
        return super()._print_Subs(expr)

def _latex_de_lado(texto: str) -> str:
    texto = texto.strip()
    if texto == "no existe":
        return r"\text{no existe}"
    limite = _LIMITE.fullmatch(texto)
    if limite:
        variable = limite["variable"]
        destino = limite["destino"]
        lado = "+-"
        if destino.endswith(("+", "-")) and destino not in ("+oo", "-oo"):
            destino, lado = destino[:-1], destino[-1]
        expresion = analizar(limite["expresion"], variable, evaluar=False)
        return sp.latex(sp.Limit(
            expresion, sp.Symbol(variable), analizar(destino, variable), dir=lado,
        ))
    derivada = _DERIVADA.fullmatch(texto)
    if derivada:
        variable = derivada["variable"]
        return (
            rf"\frac{{\mathrm{{d}}}}{{\mathrm{{d}}{variable}}}"
            rf"\left({sp.latex(analizar(derivada['expresion'], variable, evaluar=False))}\right)"
        )
    return sp.latex(analizar(texto, evaluar=False))

def latex_de_afirmacion(izquierda: str, relacion: str, derecha: str) -> str:
    original = f"{izquierda} {relacion} {derecha}"
    if relacion != "=":
        return original
    try:
        from adaptadores.salientes.simbolico.reglas_formales import analizar_regla, es_regla_formal

        if es_regla_formal(izquierda, derecha):
            variable = re.match(r'^d/d([xtz])\b', izquierda.strip())
            var = variable[1] if variable else 'x'
            lado_derecho = analizar_regla(derecha, var, evaluar=False)
            impresor = _NotacionDeRegla()
            return f"{impresor.doprint(analizar_regla(izquierda, var, evaluar=False))} = {impresor.doprint(lado_derecho)}"
        return f"{_latex_de_lado(izquierda)} = {_latex_de_lado(derecha)}"
    except (ValueError, TypeError, sp.SympifyError):
        return original
