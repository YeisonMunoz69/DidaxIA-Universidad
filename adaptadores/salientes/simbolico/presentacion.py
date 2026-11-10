"""
presentacion.py — Expresión de SymPy a JavaScript evaluable (`PM-B26`)
===========================================================================

Trae `expr_to_js`/`JSPrinter` de `Calculadora de Derivadas/repo-2/backend/
adapters/outbound/cas/sympy_parser.py`, la única pieza de esa carpeta que
`PresentationHints` necesitaba y que este repositorio no tenía —
`06-Guia-de-Reutilizacion.md` no la lista porque nunca formó parte del
`03-Prototipo-Codigo/` que esa guía audita: es de un proyecto distinto, la
propia calculadora de derivadas del equipo, consultada ahora porque `PM-B26`
la necesita y aquí no existía.

Qué se porta y qué no
--------------------------
Se porta el conversor completo: **una sola responsabilidad** —expresión de
SymPy a cadena JavaScript, para `new Function('x', 'return ' + js)` en el
cliente—, sin las otras piezas del archivo origen (`parse_expression`,
`_normalize`, la whitelist de nombres): este sistema ya tiene su propio
analizador de entrada, `adaptadores/salientes/simbolico/analizador.py`, y
traer un segundo lo duplicaría — la misma razón por la que
`06-Guia-de-Reutilizacion.md` excluyó piezas equivalentes de
`03-Prototipo-Codigo/`.

`_print_Pow` evalúa numéricamente `base ** exponente` cuando los dos son
números puros — es una simplificación de presentación, no de cálculo: el
resultado que el estudiante ve verificado sigue siendo el de
`adaptadores/salientes/simbolico/pasos.py`, esta función solo dibuja.
"""

from __future__ import annotations

import sympy as sp
from sympy.printing.pycode import PythonCodePrinter


class _JSPrinter(PythonCodePrinter):
    """Imprime JavaScript ES2016+ válido para `new Function('x', …)`.

    Hereda de `PythonCodePrinter` porque genera `x**n` (el operador `**` de
    ES2016) para todo lo que no se sobrescribe aquí; lo que se sobrescribe es
    lo que Python y JavaScript nombran distinto — `Math.sin` en vez de
    `math.sin`, sin importar módulo.
    """

    def _print_Mul(self, expr: sp.Expr) -> str:
        texto = super()._print_Mul(expr)
        # Python acepta -x**2; JavaScript exige -(x**2). Conservar el signo
        # fuera de toda la multiplicación evita cambiarlo por (-x)**2.
        return f"-({texto[1:]})" if texto.startswith("-") else texto

    def _print_Pi(self, expr: sp.Expr) -> str:
        return "Math.PI"

    def _print_Exp1(self, expr: sp.Expr) -> str:
        return "Math.E"

    def _print_Infinity(self, expr: sp.Expr) -> str:
        return "Infinity"

    def _print_NegativeInfinity(self, expr: sp.Expr) -> str:
        return "-Infinity"

    def _print_NaN(self, expr: sp.Expr) -> str:
        return "NaN"

    def _print_sin(self, expr: sp.Expr) -> str:
        return f"Math.sin({self._print(expr.args[0])})"

    def _print_cos(self, expr: sp.Expr) -> str:
        return f"Math.cos({self._print(expr.args[0])})"

    def _print_tan(self, expr: sp.Expr) -> str:
        return f"Math.tan({self._print(expr.args[0])})"

    def _print_cot(self, expr: sp.Expr) -> str:
        return f"(1/Math.tan({self._print(expr.args[0])}))"

    def _print_sec(self, expr: sp.Expr) -> str:
        return f"(1/Math.cos({self._print(expr.args[0])}))"

    def _print_csc(self, expr: sp.Expr) -> str:
        return f"(1/Math.sin({self._print(expr.args[0])}))"

    def _print_asin(self, expr: sp.Expr) -> str:
        return f"Math.asin({self._print(expr.args[0])})"

    def _print_acos(self, expr: sp.Expr) -> str:
        return f"Math.acos({self._print(expr.args[0])})"

    def _print_atan(self, expr: sp.Expr) -> str:
        return f"Math.atan({self._print(expr.args[0])})"

    def _print_sinh(self, expr: sp.Expr) -> str:
        return f"Math.sinh({self._print(expr.args[0])})"

    def _print_cosh(self, expr: sp.Expr) -> str:
        return f"Math.cosh({self._print(expr.args[0])})"

    def _print_tanh(self, expr: sp.Expr) -> str:
        return f"Math.tanh({self._print(expr.args[0])})"

    def _print_exp(self, expr: sp.Expr) -> str:
        return f"Math.exp({self._print(expr.args[0])})"

    def _print_log(self, expr: sp.Expr) -> str:
        if len(expr.args) == 1:
            return f"Math.log({self._print(expr.args[0])})"
        base = self._print(expr.args[1])
        return f"(Math.log({self._print(expr.args[0])})/Math.log({base}))"

    def _print_sqrt(self, expr: sp.Expr) -> str:
        return f"Math.sqrt({self._print(expr.args[0])})"

    def _print_Abs(self, expr: sp.Expr) -> str:
        return f"Math.abs({self._print(expr.args[0])})"

    def _print_sign(self, expr: sp.Expr) -> str:
        return f"Math.sign({self._print(expr.args[0])})"

    def _print_re(self, expr: sp.Expr) -> str:
        return self._print(expr.args[0])

    def _print_im(self, expr: sp.Expr) -> str:
        return "0"

    def _print_Derivative(self, expr: sp.Expr) -> str:
        return "1"

    def _print_Piecewise(self, expr: sp.Expr) -> str:
        result = "NaN"
        for sub_expr, cond in reversed(expr.args):
            c_str = self._print(cond)
            e_str = self._print(sub_expr)
            if cond is True or cond == sp.true:
                result = e_str
            else:
                result = f"({c_str} ? ({e_str}) : ({result}))"
        return result

    def _print_Heaviside(self, expr: sp.Expr) -> str:
        return f"({self._print(expr.args[0])} >= 0 ? 1 : 0)"

    def _print_Min(self, expr: sp.Expr) -> str:
        args = ", ".join(self._print(a) for a in expr.args)
        return f"Math.min({args})"

    def _print_Max(self, expr: sp.Expr) -> str:
        args = ", ".join(self._print(a) for a in expr.args)
        return f"Math.max({args})"

    def _print_floor(self, expr: sp.Expr) -> str:
        return f"Math.floor({self._print(expr.args[0])})"

    def _print_ceiling(self, expr: sp.Expr) -> str:
        return f"Math.ceil({self._print(expr.args[0])})"

    def _print_Pow(self, expr: sp.Expr) -> str:
        base, exponente = expr.args

        if _es_numero_puro(base) and _es_numero_puro(exponente):
            valor = _evaluar_numerico(base, exponente)
            if valor is not None:
                return valor

        if exponente == sp.Rational(1, 2):
            return f"Math.sqrt({self._print(base)})"
        if exponente == sp.Rational(1, 3):
            return f"Math.cbrt({self._print(base)})"
        if exponente == sp.Rational(-1, 2):
            return f"(1/Math.sqrt({self._print(base)}))"
        return super()._print_Pow(expr)


def _es_numero_puro(sub_expr: sp.Expr) -> bool:
    return sub_expr.is_number and not sub_expr.has(sp.Symbol)


def _evaluar_numerico(base: sp.Expr, exponente: sp.Expr) -> str | None:
    """`base ** exponente` como literal JS, o `None` si no da un real simple."""
    try:
        valor = complex(base**exponente)
    except (TypeError, ValueError, OverflowError):
        return None
    if valor.imag != 0:
        return None
    real = valor.real
    return str(int(real)) if real == int(real) else repr(real)


def expr_to_js(expr: sp.Expr) -> str:
    """`expr` como cadena JavaScript evaluable con `new Function('x', ...)`.

    No lanza: una expresión que `_JSPrinter` no sepa imprimir es un caso que
    `pasos.py`/`analizador.py` ya validaron como matemáticamente correcto, así
    que un fallo aquí es de presentación, no de cálculo.
    """
    return _JSPrinter().doprint(expr)
