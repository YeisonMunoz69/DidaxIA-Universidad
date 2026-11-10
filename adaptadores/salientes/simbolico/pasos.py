from __future__ import annotations

import sympy as sp
from sympy import Derivative, Symbol
from sympy.printing.latex import LatexPrinter

from adaptadores.salientes.simbolico.simplificacion import simplificar
from adaptadores.salientes.simbolico.tabla_trigonometrica import reglas as tabla_trigonometrica


NOTACIONES = ("lagrange", "leibniz", "operador", "euler")


NOTACION_POR_DEFECTO = "operador"


class _ImpresorPorNotacion(LatexPrinter):

    def __init__(self, settings=None, notacion: str = NOTACION_POR_DEFECTO, variable: str = "x"):
        super().__init__(settings or {})
        self.notacion = notacion
        self.variable = variable

    def _print_Derivative(self, expr):
        interior = self._print(expr.expr)
        v = str(expr.variables[0])
        if self.notacion == "lagrange":
            return r"\left[ " + interior + r" \right]'"
        if self.notacion == "euler":
            return rf"D_{{{v}}}\left[ {interior} \right]"

        return rf"\dfrac{{d}}{{d{v}}}\left[ {interior} \right]"

def _tex(expr, notacion: str = NOTACION_POR_DEFECTO, variable: str = "x") -> str:
    return _ImpresorPorNotacion(notacion=notacion, variable=variable).doprint(expr)

class MotorDePasos:

    def __init__(self, expr: sp.Expr, var: Symbol, notacion: str = NOTACION_POR_DEFECTO):
        self.var = var
        self.notacion = notacion
        self.nombre_var = str(var)
        self.pasos: list[dict] = []
        self.actual = Derivative(expr, var)

    def _paso(self, tipo: str, latex_str: str, regla: str) -> None:
        self.pasos.append({"tipo": tipo, "latex": latex_str, "regla": regla})

    def _tex(self, expr) -> str:
        return _tex(expr, self.notacion, self.nombre_var)

    def _regla_del_nodo(self, expr: sp.Expr) -> tuple[sp.Expr, str, str]:
        x, v = self.var, self.nombre_var

        if not expr.has(x):
            return sp.Integer(0), "Regla de la Constante", rf"\dfrac{{d}}{{d{v}}}[c] = 0"

        if expr == x:
            return sp.Integer(1), "Derivada de la variable", rf"\dfrac{{d}}{{d{v}}}[{v}] = 1"

        for reconocer in (self._regla_suma_o_producto, self._regla_de_funcion_conocida):
            resultado = reconocer(expr, x, v)
            if resultado is not None:
                return resultado

        return (
            sp.diff(expr, x),
            "Derivada directa (SymPy)",
            rf"\dfrac{{d}}{{d{v}}}[f] \text{{ calculada simbólicamente}}",
        )

    def _regla_suma_o_producto(self, expr: sp.Expr, x: Symbol, v: str) -> tuple[sp.Expr, str, str] | None:
        if isinstance(expr, sp.Add):
            return self._regla_suma(expr, x, v)
        if isinstance(expr, sp.Mul):
            return self._regla_producto(expr, x, v)
        return None

    def _regla_de_funcion_conocida(self, expr: sp.Expr, x: Symbol, v: str) -> tuple[sp.Expr, str, str] | None:
        if isinstance(expr, sp.exp):
            return self._regla_exponencial_base_e(expr, x, v)
        if isinstance(expr, sp.Pow):
            return self._regla_potencia(expr, x, v)
        if isinstance(expr, sp.log):
            return self._regla_logaritmo(expr, x, v)
        return self._regla_trigonometrica(expr, x, v)

    @staticmethod
    def _regla_trigonometrica(expr: sp.Expr, x: Symbol, v: str) -> tuple[sp.Expr, str, str] | None:
        for clase, (constructor, nombre, plantilla) in tabla_trigonometrica(x, v).items():
            if isinstance(expr, clase):
                arg = expr.args[0]
                nuevo = constructor(arg)
                if arg != x:
                    plantilla = plantilla + rf" \quad u = {sp.latex(arg)}"
                return nuevo, nombre, plantilla
        return None

    @staticmethod
    def _regla_suma(expr: sp.Expr, x: Symbol, v: str) -> tuple[sp.Expr, str, str]:
        terminos = expr.args
        nuevo = sp.Add(*[Derivative(t, x) for t in terminos])
        return (
            nuevo,
            "Regla de la Suma/Resta",
            rf"\dfrac{{d}}{{d{v}}}[u \pm w] = \dfrac{{d}}{{d{v}}}[u] \pm \dfrac{{d}}{{d{v}}}[w]",
        )

    @staticmethod
    def _regla_producto(expr: sp.Mul, x: Symbol, v: str) -> tuple[sp.Expr, str, str] | None:
        constantes = [a for a in expr.args if not a.has(x)]
        variables = [a for a in expr.args if a.has(x)]

        if constantes and variables:
            c = sp.Mul(*constantes)
            f = sp.Mul(*variables) if len(variables) > 1 else variables[0]
            c_tex = sp.latex(c)
            return (
                c * Derivative(f, x),
                "Regla del Múltiplo Constante",
                rf"\dfrac{{d}}{{d{v}}}[{c_tex} \cdot f] = {c_tex} \cdot \dfrac{{d}}{{d{v}}}[f]",
            )

        if not variables:
            return None

        negativos = [a for a in variables if isinstance(a, sp.Pow) and a.exp.is_number and a.exp < 0]
        positivos = [a for a in variables if a not in negativos]

        if negativos and positivos:
            u = sp.Mul(*positivos)
            w = sp.Mul(*[a.base ** (-a.exp) for a in negativos])
            nuevo = (Derivative(u, x) * w - u * Derivative(w, x)) / w ** 2
            return (
                nuevo,
                "Regla del Cociente",
                rf"\dfrac{{d}}{{d{v}}}\!\left[\dfrac{{u}}{{w}}\right] = "
                rf"\dfrac{{u' \cdot w - u \cdot w'}}{{w^2}}",
            )

        if len(variables) >= 2:
            u = variables[0]
            w = sp.Mul(*variables[1:]) if len(variables) > 2 else variables[1]
            nuevo = Derivative(u, x) * w + u * Derivative(w, x)
            return (
                nuevo,
                "Regla del Producto",
                rf"\dfrac{{d}}{{d{v}}}[u \cdot w] = u' \cdot w + u \cdot w'",
            )
        return None

    @staticmethod
    def _regla_exponencial_base_e(expr: sp.exp, x: Symbol, v: str) -> tuple[sp.Expr, str, str]:
        arg = expr.args[0]
        if arg == x:
            return expr, "Derivada de e^x", rf"\dfrac{{d}}{{d{v}}}[e^{v}] = e^{v}"
        return (
            expr * Derivative(arg, x),
            "Exponencial e^u (Regla de la Cadena)",
            rf"\dfrac{{d}}{{d{v}}}[e^u] = e^u \cdot u' \quad u = {sp.latex(arg)}",
        )

    @staticmethod
    def _regla_potencia(expr: sp.Pow, x: Symbol, v: str) -> tuple[sp.Expr, str, str] | None:
        base, exp = expr.args

        if base.has(x) and not exp.has(x):
            es_raiz = isinstance(exp, sp.Rational) and not isinstance(exp, sp.Integer)
            nombre_base = "Regla de la Potencia (Raíz)" if es_raiz else "Regla de la Potencia"
            n_tex = sp.latex(exp)
            if base == x:
                return (
                    exp * x ** (exp - 1),
                    nombre_base,
                    rf"\dfrac{{d}}{{d{v}}}[{v}^{{{n_tex}}}] = {n_tex} \cdot {v}^{{{n_tex}-1}}",
                )
            u_tex = sp.latex(base)
            return (
                exp * base ** (exp - 1) * Derivative(base, x),
                f"{nombre_base} + Cadena",
                rf"\dfrac{{d}}{{d{v}}}[u^{{{n_tex}}}] = {n_tex} \cdot u^{{{n_tex}-1}} \cdot u' "
                rf"\quad u = {u_tex}",
            )

        if not base.has(x) and exp.has(x):
            if base == sp.E:
                return (
                    expr * Derivative(exp, x),
                    "Exponencial e^u (Cadena)",
                    rf"\dfrac{{d}}{{d{v}}}[e^u] = e^u \cdot u'",
                )
            b_tex = sp.latex(base)
            return (
                expr * sp.log(base) * Derivative(exp, x),
                "Exponencial a^u (Cadena)",
                rf"\dfrac{{d}}{{d{v}}}[{b_tex}^u] = {b_tex}^u \cdot \ln({b_tex}) \cdot u'",
            )

        if base.has(x) and exp.has(x):
            nuevo = expr * (Derivative(exp, x) * sp.log(base) + exp * Derivative(base, x) / base)
            return (
                nuevo,
                "Derivación Logarítmica (u^v)",
                rf"\dfrac{{d}}{{d{v}}}[u^v] = u^v \cdot \left(v' \ln u + v \cdot \dfrac{{u'}}{{u}}\right)",
            )
        return None

    @staticmethod
    def _regla_logaritmo(expr: sp.log, x: Symbol, v: str) -> tuple[sp.Expr, str, str]:
        args = expr.args
        arg = args[0]
        if len(args) == 1:
            if arg == x:
                return sp.Integer(1) / x, "Derivada del Logaritmo Natural", rf"\dfrac{{d}}{{d{v}}}[\ln {v}] = \dfrac{{1}}{{{v}}}"
            u_tex = sp.latex(arg)
            return (
                Derivative(arg, x) / arg,
                "Derivada de ln(u) — Cadena",
                rf"\dfrac{{d}}{{d{v}}}[\ln u] = \dfrac{{u'}}{{u}} \quad u = {u_tex}",
            )
        base = args[1]
        b_tex, u_tex = sp.latex(base), sp.latex(arg)
        return (
            Derivative(arg, x) / (arg * sp.log(base)),
            f"Derivada de log_{{{b_tex}}}(u)",
            rf"\dfrac{{d}}{{d{v}}}[\log_{{{b_tex}}} u] = \dfrac{{u'}}{{u \cdot \ln {b_tex}}}",
        )

    def ejecutar(self) -> tuple[sp.Expr, sp.Expr, list[dict]]:
        v = self.nombre_var
        self._paso("inicio", self._tex(self.actual), f"Planteamiento: calcular la derivada respecto a {v}")

        tope_de_iteraciones = 150
        for _ in range(tope_de_iteraciones):
            if not self.actual.has(Derivative):
                break
            nodo = next(
                (n for n in sp.preorder_traversal(self.actual) if isinstance(n, Derivative)),
                None,
            )
            if nodo is None:
                break
            nuevo_nodo, nombre_regla, latex_regla = self._regla_del_nodo(nodo.expr)
            self.actual = self.actual.subs(nodo, nuevo_nodo)
            self._paso("regla", self._tex(self.actual), f"{nombre_regla}: ${latex_regla}$")

        bruto = self.actual
        if bruto.has(Derivative):
            bruto = sp.diff(bruto.doit(), self.var)

        simplificado = simplificar(bruto)
        if str(simplificado) != str(bruto):
            self._paso("simplificacion", rf"= {sp.latex(simplificado)}", "Forma simplificada")
            final = simplificado
        else:
            final = bruto

        self._paso("resultado_final", self._linea_de_resultado(final), "Resultado final de la derivada")
        return bruto, final, self.pasos

    def _linea_de_resultado(self, final: sp.Expr) -> str:
        v = self.nombre_var
        cuerpo = sp.latex(final)
        if self.notacion == "leibniz":
            return rf"\dfrac{{dy}}{{d{v}}} = {cuerpo}"
        if self.notacion == "operador":
            return rf"\dfrac{{d}}{{d{v}}}\left[ f({v}) \right] = {cuerpo}"
        if self.notacion == "euler":
            return rf"D_{{{v}}}\left[ f({v}) \right] = {cuerpo}"
        return rf"f'({v}) = {cuerpo}"
