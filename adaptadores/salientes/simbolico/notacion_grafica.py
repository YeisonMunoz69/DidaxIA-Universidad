"""Notación editorial adicional para funciones de la graficadora.

Sólo traduce escritura matemática explícita. El analizador común conserva
la lista de nombres, la frontera léxica y la validación de variables.
"""

from __future__ import annotations

import re


def _grupo(texto: str, inicio: int, abrir: str, cerrar: str) -> tuple[str, int]:
    if inicio >= len(texto) or texto[inicio] != abrir:
        raise ValueError("faltan paréntesis o llaves en la fórmula")
    nivel = 0
    for indice in range(inicio, len(texto)):
        if texto[indice] == abrir:
            nivel += 1
        elif texto[indice] == cerrar:
            nivel -= 1
            if nivel == 0:
                return texto[inicio + 1:indice], indice + 1
    raise ValueError("hay paréntesis o llaves sin cerrar en la fórmula")


def _indice(texto: str, inicio: int) -> tuple[str, int]:
    inicio += len(texto[inicio:]) - len(texto[inicio:].lstrip())
    if inicio < len(texto) and texto[inicio] in "{(":
        abrir = texto[inicio]
        return _grupo(texto, inicio, abrir, "}" if abrir == "{" else ")")
    encontrado = re.match(r"\d+", texto[inicio:])
    if not encontrado:
        raise ValueError("escribe el exponente o la base entre llaves")
    return encontrado.group(), inicio + encontrado.end()


def _validar_anidamiento(s: str) -> None:
    # Limitar el anidamiento antes de las sustituciones recursivas.
    nivel = 0
    for caracter in s:
        if caracter in "({[":
            nivel += 1
            if nivel > 32:
                raise ValueError("la fórmula supera 32 niveles de anidamiento")
        elif caracter in ")}]":
            nivel -= 1
    if re.search(r"\\(?:lim|int)\b|\\(?:d|t)?frac\s*\{\s*d\s*\}\s*\{\s*d[A-Za-z]\s*\}", s):
        raise ValueError("para Función escribe la expresión, sin operadores de derivada, límite o integral")


def normalizar_funcion_grafica(texto: str, *, raices_reales: bool = True) -> str:
    s = texto.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    _validar_anidamiento(s)
    # MathLive y libros suelen envolver sen en operatorname{mathrm{sen}}.
    envoltura = re.compile(r"\\(?:operatorname\*?|mathrm|mathbf|mathit|text)\s*\{([^{}]+)\}")
    while envoltura.search(s):
        s = envoltura.sub(r"\1", s)
    s = re.sub(r"\\(?:left|right|bigl|bigr|Bigl|Bigr|big|Big|bigg|Bigg)\b\s*", "", s)
    s = re.sub(r"\\(?:[,;!:]|quad\b|qquad\b|enspace\b)", " ", s)
    s = s.replace(r"\exponentialE", "e")

    # Raíces de índice explícito: las impares se interpretan como raíces reales.
    patron_raiz = re.compile(r"\\sqrt\s*\[\s*(\d+)\s*\]\s*")
    while coincidencia := patron_raiz.search(s):
        indice = int(coincidencia.group(1))
        if not 2 <= indice <= 16:
            raise ValueError("el índice de la raíz debe estar entre 2 y 16")
        argumento, fin = _grupo(s, coincidencia.end(), "{", "}")
        argumento = normalizar_funcion_grafica(argumento, raices_reales=raices_reales)
        raiz = (f"(sign(({argumento}))*Abs(({argumento}))^(1/{indice}))" if indice % 2 and raices_reales
                else f"(({argumento})^(1/{indice}))")
        s = s[:coincidencia.start()] + raiz + s[fin:]

    # log_b(argumento), con base y argumento explícitos, incluso anidados.
    patron_log = re.compile(r"\\log\s*_\s*")
    while coincidencia := patron_log.search(s):
        base, fin_base = _indice(s, coincidencia.end())
        inicio_arg = fin_base + len(s[fin_base:]) - len(s[fin_base:].lstrip())
        argumento, fin = _grupo(s, inicio_arg, "(", ")")
        s = s[:coincidencia.start()] + f"log(({argumento}),({base}))" + s[fin:]

    # sin²(u) significa (sin(u))², no sin(u²) ni una nueva función.
    patron_trig = re.compile(r"(?<![A-Za-z])\\?(sin|sen|cos|tan|tg|cot|sec|csc|sinh|cosh|tanh)\s*\^")
    while coincidencia := patron_trig.search(s):
        potencia, fin_potencia = _indice(s, coincidencia.end())
        inicio_arg = fin_potencia + len(s[fin_potencia:]) - len(s[fin_potencia:].lstrip())
        argumento, fin = _grupo(s, inicio_arg, "(", ")")
        s = s[:coincidencia.start()] + f"(({coincidencia.group(1)}({argumento}))^({potencia}))" + s[fin:]
    return s
