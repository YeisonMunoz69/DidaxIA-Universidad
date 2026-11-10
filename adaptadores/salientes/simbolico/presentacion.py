from __future__ import annotations

import sympy as sp
from sympy.printing.pycode import PythonCodePrinter


class _JSPrinter(PythonCodePrinter):

    def _print_Mul(self, expr: sp.Expr) -> str:
        texto = super()._print_Mul(expr)

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
    try:
        valor = complex(base**exponente)
    except (TypeError, ValueError, OverflowError):
        return None
    if valor.imag != 0:
        return None
    real = valor.real
    return str(int(real)) if real == int(real) else repr(real)

def expr_to_js(expr: sp.Expr) -> str:
    return _JSPrinter().doprint(expr)
