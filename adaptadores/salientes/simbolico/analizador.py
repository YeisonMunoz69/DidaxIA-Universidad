from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

from adaptadores.salientes.simbolico.guardia import EntradaNoAdmitida, exigir_entrada_admisible
from adaptadores.salientes.simbolico.notacion_grafica import normalizar_funcion_grafica
from dominio.modelo.notacion_entrada import normalizar_escritura_matematica

_TRANSFORMACIONES = standard_transformations + (convert_xor, implicit_multiplication)


_NOMBRES_PERMITIDOS: dict = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "acot": sp.acot, "asec": sp.asec, "acsc": sp.acsc,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan,
    "arccot": sp.acot, "arcsec": sp.asec, "arccsc": sp.acsc,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "coth": sp.coth, "sech": sp.sech, "csch": sp.csch,
    "exp": sp.exp, "log": sp.log, "ln": sp.log,
    "log10": lambda x: sp.log(x, 10), "log2": lambda x: sp.log(x, 2),
    "sqrt": sp.sqrt, "cbrt": lambda x: x ** sp.Rational(1, 3),
    "Abs": sp.Abs, "abs": sp.Abs, "sign": sp.sign,

    "Piecewise": sp.Piecewise, "Eq": sp.Eq,
    "pi": sp.pi, "e": sp.E, "E": sp.E, "oo": sp.oo, "inf": sp.oo,

    "sen": sp.sin, "senh": sp.sinh,
    "tg": sp.tan, "cotg": sp.cot, "ctg": sp.cot,
    "arcsen": sp.asin, "arctg": sp.atan, "raiz": sp.sqrt,

    "Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float,
    "Rational": sp.Rational, "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow,
    "Lt": sp.Lt, "Le": sp.Le, "Gt": sp.Gt, "Ge": sp.Ge, "Ne": sp.Ne,
}

_VARIABLES_EXTRA = ("y", "z", "t", "u", "v", "a", "b", "c", "n", "k")


def _desarmar_bloque_llaves(s: str, pos_inicio: int) -> tuple[str, int] | None:
    if pos_inicio >= len(s) or s[pos_inicio] != "{":
        return None
    nivel = 0
    i = pos_inicio
    while i < len(s):
        if s[i] == "{":
            nivel += 1
        elif s[i] == "}":
            nivel -= 1
            if nivel == 0:
                return s[pos_inicio + 1 : i], i + 1
        i += 1
    return None

def _desarmar_fracciones_latex(s: str) -> str:
    patron = re.compile(r"\\(?:d|t)?frac\s*\{")
    while True:
        m = patron.search(s)
        if not m:
            break
        inicio = m.start()
        llave1_inicio = m.end() - 1
        res1 = _desarmar_bloque_llaves(s, llave1_inicio)
        if not res1:
            break
        num, fin1 = res1
        resto = s[fin1:]
        m2 = re.match(r"^\s*\{", resto)
        if not m2:
            break
        llave2_inicio = fin1 + m2.end() - 1
        res2 = _desarmar_bloque_llaves(s, llave2_inicio)
        if not res2:
            break
        den, fin2 = res2
        s = s[:inicio] + f"(({num})/({den}))" + s[fin2:]
    return s

def _desarmar_raices_latex(s: str) -> str:
    s = re.sub(r"\\sqrt\[([^{}]+)\]\{([^{}]+)\}", r"((\2)^(1/(\1)))", s)
    patron = re.compile(r"\\sqrt\s*\{")
    while True:
        m = patron.search(s)
        if not m:
            break
        inicio = m.start()
        llave_inicio = m.end() - 1
        res = _desarmar_bloque_llaves(s, llave_inicio)
        if not res:
            break
        arg, fin = res
        s = s[:inicio] + f"sqrt({arg})" + s[fin:]
    return s

def _normalizar_texto(texto: str, variable: str = "x") -> str:
    s = normalizar_escritura_matematica(texto)

    s = re.sub(r"\\left\s*\[", "(", s)
    s = re.sub(r"\\right\s*\]", ")", s)
    s = normalizar_funcion_grafica(s, raices_reales=False)
    if s.startswith("$") and s.endswith("$") and len(s) >= 2:
        s = s[1:-1].strip()
    if s.startswith(r"\(") and s.endswith(r"\)") and len(s) >= 4:
        s = s[2:-2].strip()

    s = _desarmar_fracciones_latex(s)
    s = _desarmar_raices_latex(s)

    s = re.sub(r"\\left\s*\(", "(", s)
    s = re.sub(r"\\right\s*\)", ")", s)
    s = re.sub(r"\\left\s*\[", "(", s)
    s = re.sub(r"\\right\s*\]", ")", s)
    s = re.sub(r"\\left\s*\\\{", "(", s)
    s = re.sub(r"\\right\s*\\\}", ")", s)
    s = re.sub(r"\\left\s*\|([^{}|]+)\\right\s*\|", r"Abs(\1)", s)
    s = re.sub(r"\\vert\s*([^{}\\]+)\s*\\vert", r"Abs(\1)", s)
    s = re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)

    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    s = s.replace(r"\pi", "pi")

    s = re.sub(r"\\(?:text|mathrm|mathbf|mathit)\{([^{}]+)\}", r"\1", s)

    s = re.sub(
        r"\\(sin|cos|tan|cot|sec|csc|asin|acos|atan|sinh|cosh|tanh|coth|sech|csch|ln|log|exp|sen|senh|tg|cotg|ctg|arcsen|arctg|sqrt|abs|sign)\b",
        r"\1",
        s,
    )

    s = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", s)
    s = re.sub(r"_\{([^{}]+)\}", r"_(\1)", s)
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("\\", "")

    s = s.replace("−", "-")
    s = s.replace("·", "*").replace("×", "*")
    s = s.replace("²", "^2").replace("³", "^3").replace("¹", "^1")
    s = s.replace("⁴", "^4").replace("⁵", "^5").replace("⁶", "^6")
    s = s.replace("⁷", "^7").replace("⁸", "^8").replace("⁹", "^9")
    s = s.replace("√", "sqrt")
    s = s.replace("**", "^")

    s = re.sub(rf"\b{re.escape(variable)}\s*'(?=\s*(?:[+\-*/^)]|$))", variable, s)

    s = re.sub(r"\bSEN\b", "sin", s, flags=re.IGNORECASE)
    s = re.sub(r"\bSENH\b", "sinh", s, flags=re.IGNORECASE)
    s = re.sub(r"\bTG\b", "tan", s, flags=re.IGNORECASE)
    s = re.sub(r"\bCTG\b", "cot", s, flags=re.IGNORECASE)
    s = re.sub(r"\bLN\b", "log", s, flags=re.IGNORECASE)
    s = re.sub(r"\bARCSEN\b", "asin", s, flags=re.IGNORECASE)
    s = re.sub(r"\bARCTG\b", "atan", s, flags=re.IGNORECASE)

    s = re.sub(r"(?<![A-Za-z])([A-Za-z])(\d+)", r"\1^\2", s)
    return s.strip()

def analizar(texto: str, variable: str = "x", *, evaluar: bool = True, real: bool = False) -> sp.Expr:
    normalizado = _normalizar_texto(texto, variable)
    exigir_entrada_admisible(normalizado)

    nombres = dict(_NOMBRES_PERMITIDOS)
    nombres[variable] = sp.Symbol(variable, real=True) if real else sp.Symbol(variable)
    for extra in _VARIABLES_EXTRA:
        nombres.setdefault(extra, sp.Symbol(extra))

    try:
        analizada = parse_expr(
            normalizado,
            local_dict=nombres,
            global_dict={"__builtins__": {}},
            transformations=_TRANSFORMACIONES,
            evaluate=evaluar,
        )
        desconocidos = {str(s) for s in analizada.free_symbols} - {variable, *_VARIABLES_EXTRA}
        if desconocidos:
            raise EntradaNoAdmitida(
                "símbolos no reconocidos en la expresión: " + ", ".join(sorted(desconocidos))
            )
        return analizada
    except EntradaNoAdmitida:
        raise
    except Exception as e:
        raise ValueError(f"no se pudo interpretar la expresión «{texto}»: {e}") from e
