"""Álgebra de reglas generales: funciones diferenciables y parámetros constantes.

Esta gramática no cambia el analizador de ejercicios ni evalúa código Python.
Construye un árbol SymPy desde una lista cerrada de nodos AST; la igualdad
debe demostrarse simbólicamente, nunca mediante ejemplos numéricos.
"""
from __future__ import annotations

import ast
import re

import sympy as sp

from adaptadores.salientes.simbolico.analizador import _normalizar_texto
from adaptadores.salientes.simbolico.guardia import EntradaNoAdmitida, exigir_entrada_admisible

_FUNCIONES = 'fguv'
_PARAMETROS = 'abckmn'
_ELEMENTALES = {
    'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan, 'sec': sp.sec,
    'csc': sp.csc, 'cot': sp.cot, 'asin': sp.asin, 'acos': sp.acos,
    'atan': sp.atan, 'exp': sp.exp, 'log': sp.log, 'ln': sp.log,
    'sqrt': sp.sqrt, 'Abs': sp.Abs,
}


class _Arbol:
    def __init__(self, variable, evaluar=True):
        self.x = sp.Symbol(variable)
        self.evaluar = evaluar
        self.funciones = {nombre: sp.Function(nombre) for nombre in _FUNCIONES}

    def construir(self, nodo):
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            if abs(nodo.value) > 1000000:
                raise EntradaNoAdmitida('constante fuera del presupuesto')
            return sp.sympify(nodo.value)
        if isinstance(nodo, ast.Name):
            return self._nombre(nodo.id)
        if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.UAdd, ast.USub)):
            valor = self.construir(nodo.operand)
            return -valor if isinstance(nodo.op, ast.USub) else valor
        if isinstance(nodo, ast.BinOp):
            return self._operacion(nodo)
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and not nodo.keywords:
            return self._llamada(nodo.func.id, [self.construir(a) for a in nodo.args])
        raise EntradaNoAdmitida('operación fuera de la gramática de reglas')

    def _nombre(self, nombre):
        if nombre in ('e', 'E', 'pi'):
            return sp.pi if nombre == 'pi' else sp.E
        if nombre in self.funciones:
            return self.funciones[nombre](self.x)
        if nombre in (str(self.x), 'h', *_PARAMETROS):
            return sp.Symbol(nombre)
        raise EntradaNoAdmitida('nombre fuera de la gramática de reglas')

    def _operacion(self, nodo):
        izq, der = self.construir(nodo.left), self.construir(nodo.right)
        opciones = dict(evaluate=self.evaluar)
        operaciones = {ast.Add: lambda: sp.Add(izq, der, **opciones),
                       ast.Sub: lambda: sp.Add(izq, sp.Mul(-1, der, **opciones), **opciones),
                       ast.Mult: lambda: sp.Mul(izq, der, **opciones),
                       ast.Div: lambda: sp.Mul(izq, sp.Pow(der, -1, **opciones), **opciones)}
        if type(nodo.op) in operaciones:
            return operaciones[type(nodo.op)]()
        if isinstance(nodo.op, ast.Pow):
            if der.is_number and (not der.is_real or abs(der) > 100):
                raise EntradaNoAdmitida('potencia fuera del presupuesto')
            return sp.Pow(izq, der, **opciones)
        raise EntradaNoAdmitida('operador fuera de la gramática de reglas')

    def _llamada(self, nombre, args):
        if nombre in self.funciones and len(args) == 1:
            return self.funciones[nombre](*args)
        if nombre in _ELEMENTALES and 1 <= len(args) <= (2 if nombre in ('log', 'ln') else 1):
            return _ELEMENTALES[nombre](*args)
        if nombre in ('D', 'Derivative', 'diff') and len(args) in (1, 2):
            var = args[1] if len(args) == 2 else self.x
            if var != self.x:
                raise EntradaNoAdmitida('derivación formal respecto a otra variable')
            return sp.Derivative(args[0], self.x, evaluate=False)
        if nombre in ('df', 'dg', 'du', 'dv') and len(args) == 1:
            if args[0] == self.x:
                return sp.Derivative(self.funciones[nombre[1]](self.x), self.x, evaluate=False)
            auxiliar = sp.Dummy('argumento')
            return sp.Subs(sp.Derivative(self.funciones[nombre[1]](auxiliar), auxiliar), auxiliar, args[0])
        raise EntradaNoAdmitida('función fuera de la gramática de reglas')


def es_regla_formal(izquierda: str, derecha: str) -> bool:
    """No abre esta gramática para una igualdad algebraica ordinaria."""
    texto = izquierda + ' ' + derecha
    incrustado = any(re.search(r'd/d[xtz]', lado) and not re.fullmatch(r'\s*d/d[xtz]\s*\(.+\)\s*', lado, re.S)
                     for lado in (izquierda, derecha))
    return bool(re.search(r"\b[fguv]\s*(?:\(|['′]|\\prime)|\bh\b|\b(?:Derivative|diff)\s*\(", texto)
                or len(re.findall(r'd/d[xtz]', texto)) > 1 or incrustado)


def _operadores_agrupados(texto):
    """Cada operador conserva su alcance: (d/dx A) por (d/dx B)."""
    for _ in range(20):
        operadores = list(re.finditer(r'd/d([xtz])\s*\(', texto))
        if not operadores:
            return texto
        m = operadores[-1]
        inicio = m.end() - 1
        nivel, fin = 1, inicio + 1
        while fin < len(texto) and nivel:
            nivel += (texto[fin] == '(') - (texto[fin] == ')')
            fin += 1
        if nivel:
            raise EntradaNoAdmitida('operador sin cierre')
        texto = texto[:m.start()] + f'Derivative({texto[inicio+1:fin-1]},{m[1]})' + texto[fin:]
    raise EntradaNoAdmitida('demasiados operadores')


def _primas(texto: str) -> str:
    texto = texto.replace('′', "'").replace('’', "'")
    texto = re.sub(r"\b([fguv])\s*(?:\^?\{?\\prime\}?|')\s*(?=\()", r'd\1', texto)
    texto = re.sub(r"\b([fguv])\s*'", r'd\1(x)', texto)
    # (u*v)' y (f(x)/g(x))': una prima aplicada al grupo completo.
    while "'" in texto:
        fin = texto.index("'")
        cierre = fin - 1
        while cierre >= 0 and texto[cierre].isspace():
            cierre -= 1
        if cierre < 0 or texto[cierre] != ')':
            raise EntradaNoAdmitida('prima sin función o grupo delimitado')
        nivel, inicio = 1, cierre - 1
        while inicio >= 0 and nivel:
            nivel += (texto[inicio] == ')') - (texto[inicio] == '(')
            inicio -= 1
        if nivel:
            raise EntradaNoAdmitida('grupo de derivada sin apertura')
        inicio += 1
        texto = texto[:inicio] + 'D(' + texto[inicio:cierre+1] + ')' + texto[fin+1:]
    return texto


def _incremento_ligado(texto):
    # Delta x es el incremento ligado por este límite, no una nueva función.
    if re.match(r'^lim\s*_\{\s*(?:\\Delta|Delta)\s*x\s*(?:->|\\to)\s*0\s*\}', texto):
        return re.sub(r'(?:\\Delta|Delta)\s*x\b', 'h', texto)
    return texto


def analizar_regla(texto: str, variable: str = 'x', *, evaluar=True) -> sp.Expr:
    """f/g/u/v son funciones; a/b/c/k/m/n no dependen de la variable."""
    if variable not in ('x', 't', 'z'):
        raise EntradaNoAdmitida('variable formal no admitida')
    if len(texto) > 500:
        raise EntradaNoAdmitida('regla demasiado extensa')
    texto = _incremento_ligado(texto.strip().strip('$').strip())
    texto = re.sub(r'\\frac\{d\}\{d([xtz])\}', r'd/d\1 ', texto)
    texto = _primas(texto)
    limite = re.match(r'^lim\s*(?:_\{\s*h\s*(?:->|\\to)\s*0\s*\}|h\s*->\s*0)\s*(.+)$', texto, re.S)
    if limite:
        texto = limite[1]
    texto = _operadores_agrupados(texto)
    operador = re.match(r'^d/d([xtz])\s*(.+)$', texto, re.S)
    if operador:
        variable, texto = operador.groups()
        texto = texto.strip()
        if texto.startswith('[') and texto.endswith(']'):
            texto = '(' + texto[1:-1] + ')'
    normal = _normalizar_texto(texto, variable).replace('^', '**')
    exigir_entrada_admisible(normal)
    # Multiplicación implícita únicamente entre tokens inequívocos.
    normal = re.sub(r'(?<=\d)(?=[a-zA-Z])', '*', normal)
    normal = re.sub(r'\b([abckmn])(?=[xtz]\b)', r'\1*', normal)
    normal = re.sub(r'(?<=\))(?=\(|[a-zA-Z])', '*', normal)
    try:
        arbol = ast.parse(normal, mode='eval')
    except SyntaxError as exc:
        raise EntradaNoAdmitida('notación de regla no reconocida') from exc
    if sum(1 for _ in ast.walk(arbol)) > 180:
        raise EntradaNoAdmitida('regla demasiado compleja')
    resultado = _Arbol(variable, evaluar=evaluar).construir(arbol.body)
    if operador:
        resultado = sp.Derivative(resultado, sp.Symbol(variable), evaluate=False)
    if limite:
        resultado = sp.Limit(resultado, sp.Symbol('h'), 0, dir='+-')
    return resultado


def _definicion_de_derivada(expr, variable):
    """La definición tiene el cociente incremental exacto, bajo derivabilidad.

    SymPy deja sin evaluar el límite de una función sin expresión conocida.
    Se comprueba algebraicamente su forma definitoria, no se aproxima con
    valores numéricos ni se declara válido cualquier límite con funciones.
    """
    if not isinstance(expr, sp.Limit):
        return expr.doit()
    cociente, incremento, destino, _ = expr.args
    if incremento != sp.Symbol('h') or destino != 0:
        return expr
    x = sp.Symbol(variable)
    if not any(str(f.func) in _FUNCIONES for f in expr.atoms(sp.Function)):
        return expr.doit()
    for nombre in _FUNCIONES:
        funcion = sp.Function(nombre)
        esperado = (funcion(x + incremento) - funcion(x)) / incremento
        if sp.simplify(cociente - esperado) == 0:
            return sp.diff(funcion(x), x)
    return expr


def comprobar_regla(izquierda: str, derecha: str) -> bool | None:
    """None significa que esta gramática no pudo comprobar la afirmación."""
    try:
        variable = re.match(r'^d/d([xtz])\b', izquierda.strip())
        var = variable[1] if variable else 'x'
        izq = _definicion_de_derivada(analizar_regla(izquierda, var), var)
        der = _definicion_de_derivada(analizar_regla(derecha, var), var)
        if izq.has(sp.Limit) or der.has(sp.Limit):
            return None
        if izq.has(sp.zoo, sp.nan, sp.oo) or der.has(sp.zoo, sp.nan, sp.oo):
            return None
        return sp.simplify(izq - der) == 0
    except (ValueError, TypeError, SyntaxError, sp.SympifyError):
        return None
