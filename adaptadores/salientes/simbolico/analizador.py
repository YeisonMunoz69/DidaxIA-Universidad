"""
analizador.py — Analizador de expresiones matemáticas sobre SymPy
===================================================================

`ADR-013` §6 trae el motor de «Calculadora de Derivadas/repo-2/backend/
adapters/outbound/cas/sympy_parser.py» (276 líneas). Este archivo es la parte
de ese módulo que **sí está conectada** al resto del motor —el analizador que
`sympy_adapter.py` invoca en cada cálculo—: normalización de texto, alias en
español y lista blanca de nombres para `parse_expr`.

Qué NO entra de `sympy_parser.py`, y por qué
----------------------------------------------
`expr_to_js` y su `JSPrinter` (~100 de las 276 líneas) traducen una expresión a
una función JavaScript para la gráfica interactiva del frontend de origen.
`ADR-013` §6.3 es explícito: *«los campos `f_js`, `df_js` y `graph` del módulo
son detalles de presentación y no entran al contexto del generador»* — van a
la capa de presentación, que hoy es enteramente de Fabián
(`codigo/frontend/`) y no se toca en esta sesión. Traerlos aquí sería courte
código sin una sola prueba que lo cubra ni un requisito al que trazarlo
(`06-Guia-de-Reutilizacion.md` §2.1), justo lo que la guía de reutilización
prohíbe. Si el frontend necesita renderizar la gráfica con datos del backend,
se trae entonces, con su propio requisito.

Qué se corrige al traerlo (`06-Guia-de-Reutilizacion.md` veredicto 🔧)
------------------------------------------------------------------------
La frontera léxica (`assert_safe_expression` del `input_guard.py` de origen)
**no se duplica**: ya existe en este repositorio como
`adaptadores/salientes/simbolico/guardia.py`, con la misma regla y el mismo
motivo (`().__class__.__bases__` se resolvía sin error). `analizar()` la
invoca en vez de traer una segunda copia — `ADR-008` K4 pide una sola forma
canónica, y dos guardianes léxicos casi idénticos son exactamente el tipo de
duplicación que esa regla previene.
"""

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

#: Lista blanca de nombres para `parse_expr`. Incluye las funciones del
#: alcance comprometido (`01-Definicion-del-Alcance.md` §3: potencia,
#: producto, cociente, cadena, trigonométricas, exponenciales, logarítmicas)
#: y los alias en español, porque `RNF-ADF` opera el sistema en español.
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
    # Casos de continuidad y límites laterales del taller. La entrada sigue
    # pasando por el guardián y se rechaza si introduce otras variables.
    "Piecewise": sp.Piecewise, "Eq": sp.Eq,
    "pi": sp.pi, "e": sp.E, "E": sp.E, "oo": sp.oo, "inf": sp.oo,
    # Alias en español.
    "sen": sp.sin, "senh": sp.sinh,
    "tg": sp.tan, "cotg": sp.cot, "ctg": sp.cot,
    "arcsen": sp.asin, "arctg": sp.atan, "raiz": sp.sqrt,
    # Internos que `parse_expr` necesita para construir números y árboles con
    # `__builtins__` bloqueado — sin esta entrada, `auto_number` genera
    # `Integer(...)` y el análisis falla en dirección segura pero inutilizable.
    "Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float,
    "Rational": sp.Rational, "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow,
    "Lt": sp.Lt, "Le": sp.Le, "Gt": sp.Gt, "Ge": sp.Ge, "Ne": sp.Ne,
}

_VARIABLES_EXTRA = ("y", "z", "t", "u", "v", "a", "b", "c", "n", "k")


def _desarmar_bloque_llaves(s: str, pos_inicio: int) -> tuple[str, int] | None:
    """Extrae el contenido de un bloque `{...}` balanceado comenzando en `pos_inicio`."""
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
    """Limpia el texto del estudiante antes de tokenizarlo.

    Cubre sintaxis LaTeX (`\\frac`, `\\sqrt`, `\\sin`, delimitadores `$`),
    unicode (menos, punto medio, superíndices, raíz), el atajo de
    escribir `x3` por `x^3` que se usa al escribir a mano, y los alias en
    español que no son nombres de función —`SEN`, `TG`, `LN`—.
    """
    # Misma escritura editorial que en Funciones, conservando aquí la
    # interpretación algebraica de raíces del verificador.
    s = normalizar_escritura_matematica(texto)
    # Conservar el significado de los delimitadores antes de quitar left/right.
    s = re.sub(r"\\left\s*\[", "(", s)
    s = re.sub(r"\\right\s*\]", ")", s)
    s = normalizar_funcion_grafica(s, raices_reales=False)
    if s.startswith("$") and s.endswith("$") and len(s) >= 2:
        s = s[1:-1].strip()
    if s.startswith(r"\(") and s.endswith(r"\)") and len(s) >= 4:
        s = s[2:-2].strip()

    # Desarmar macros de LaTeX estructurales
    s = _desarmar_fracciones_latex(s)
    s = _desarmar_raices_latex(s)

    # Delimitadores LaTeX y valor absoluto
    s = re.sub(r"\\left\s*\(", "(", s)
    s = re.sub(r"\\right\s*\)", ")", s)
    s = re.sub(r"\\left\s*\[", "(", s)
    s = re.sub(r"\\right\s*\]", ")", s)
    s = re.sub(r"\\left\s*\\\{", "(", s)
    s = re.sub(r"\\right\s*\\\}", ")", s)
    s = re.sub(r"\\left\s*\|([^{}|]+)\\right\s*\|", r"Abs(\1)", s)
    s = re.sub(r"\\vert\s*([^{}\\]+)\s*\\vert", r"Abs(\1)", s)
    s = re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)

    # Operadores y constantes
    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    s = s.replace(r"\pi", "pi")

    # Formatos de texto
    s = re.sub(r"\\(?:text|mathrm|mathbf|mathit)\{([^{}]+)\}", r"\1", s)

    # Nombres de funciones con barra invertida
    s = re.sub(
        r"\\(sin|cos|tan|cot|sec|csc|asin|acos|atan|sinh|cosh|tanh|coth|sech|csch|ln|log|exp|sen|senh|tg|cotg|ctg|arcsen|arctg|sqrt|abs|sign)\b",
        r"\1",
        s,
    )

    # Reemplazo de llaves residuales
    s = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", s)
    s = re.sub(r"_\{([^{}]+)\}", r"_(\1)", s)
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("\\", "")

    # Limpieza unicode y caracteres matemáticos
    s = s.replace("−", "-")                       # menos unicode
    s = s.replace("·", "*").replace("×", "*")  # · × → *
    s = s.replace("²", "^2").replace("³", "^3").replace("¹", "^1")
    s = s.replace("⁴", "^4").replace("⁵", "^5").replace("⁶", "^6")
    s = s.replace("⁷", "^7").replace("⁸", "^8").replace("⁹", "^9")
    s = s.replace("√", "sqrt")                     # √ → sqrt
    s = s.replace("**", "^")

    # Compatibilidad con la escritura observada en el redactor: al pegar
    # ``x'/sqrt(...)`` se pretendía la misma variable independiente que al
    # construir la fracción desde el tablero. Una prima suelta sobre ESA
    # variable no nombra una segunda función que el trazador pueda evaluar;
    # se conserva en el texto original para presentación, pero el CAS recibe
    # la variable canónica. No se toca ``f'(x)``, cuya forma completa tiene
    # significado propio y se segmenta por otra regla.
    s = re.sub(rf"\b{re.escape(variable)}\s*'(?=\s*(?:[+\-*/^)]|$))", variable, s)

    # Alias en español
    s = re.sub(r"\bSEN\b", "sin", s, flags=re.IGNORECASE)
    s = re.sub(r"\bSENH\b", "sinh", s, flags=re.IGNORECASE)
    s = re.sub(r"\bTG\b", "tan", s, flags=re.IGNORECASE)
    s = re.sub(r"\bCTG\b", "cot", s, flags=re.IGNORECASE)
    s = re.sub(r"\bLN\b", "log", s, flags=re.IGNORECASE)
    s = re.sub(r"\bARCSEN\b", "asin", s, flags=re.IGNORECASE)
    s = re.sub(r"\bARCTG\b", "atan", s, flags=re.IGNORECASE)

    # Atajo de potencia a mano: x3, x10 -> x^3, x^10
    s = re.sub(r"(?<![A-Za-z])([A-Za-z])(\d+)", r"\1^\2", s)
    return s.strip()


def analizar(texto: str, variable: str = "x", *, evaluar: bool = True, real: bool = False) -> sp.Expr:
    """Convierte texto en `sympy.Expr`, validado en dos capas independientes.

    `_normalizar_texto` estandariza primero la expresión (incluyendo LaTeX);
    `exigir_entrada_admisible` (capa léxica, `guardia.py`) valida la forma
    canónica resultante; y finalmente `parse_expr` construye el árbol simbólico
    con `__builtins__` bloqueado y lista blanca de nombres.
    """
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
    except Exception as e:                                          # noqa: BLE001
        raise ValueError(f"no se pudo interpretar la expresión «{texto}»: {e}") from e
