from __future__ import annotations

import math

import sympy as sp
from sympy.core.relational import Relational


def numero_real(valor):
    if valor is None or valor.is_real is not True or valor.is_finite is not True:
        return None
    try:
        numero = float(valor.evalf())
        return numero if math.isfinite(numero) else None
    except (ValueError, TypeError, OverflowError):
        return None

def valor_original(expr, x, a):
    if expr == x:
        return a
    if not expr.args:
        return expr
    if isinstance(expr, sp.Piecewise):
        for rama, condicion in expr.args:
            if condicion.subs(x, a) == sp.true:
                return valor_original(rama, x, a)
        return sp.nan
    if isinstance(expr, Relational):
        return expr.subs(x, a)
    argumentos = [valor_original(arg, x, a) for arg in expr.args]
    if any(v in (sp.nan, sp.zoo, sp.oo, -sp.oo) for v in argumentos):
        return sp.nan
    return expr.func(*argumentos)

def fronteras(expr, x):
    candidatos = set()
    ecuaciones = set()
    for parte in sp.preorder_traversal(expr):
        if isinstance(parte, sp.Pow) and (parte.exp.is_negative or parte.exp.is_integer is False):
            ecuaciones.add(parte.base)
        elif parte.func in (sp.log, sp.Abs, sp.sign):
            ecuaciones.add(parte.args[0])
        elif isinstance(parte, Relational):
            ecuaciones.add(parte.lhs - parte.rhs)
    for ecuacion in ecuaciones:

        try:
            soluciones = sp.solveset(ecuacion, x, domain=sp.S.Reals)
        except (ValueError, NotImplementedError):
            continue
        if isinstance(soluciones, sp.FiniteSet):
            candidatos.update(v for v in soluciones if numero_real(v) is not None)
    return sorted(candidatos, key=lambda v: float(v))[:16]

def rama_lateral(expr, x, a, lado):
    epsilon = sp.Dummy('epsilon', positive=True)
    def elegir(pieza):
        for rama, condicion in pieza.args:
            prueba = sp.simplify(condicion.subs(x, a + lado * epsilon))
            if prueba == sp.true:
                return rama_lateral(rama, x, a, lado)
            if prueba == sp.false:
                continue
            if any(not (rel.lhs - rel.rhs).is_polynomial(x) for rel in condicion.atoms(Relational)):
                raise ValueError('condición lateral no decidida simbólicamente')

            raices = fronteras(condicion, x)
            distancias = [abs(v - a) for v in raices if v != a]
            paso = min(distancias, default=sp.Integer(1)) / 2
            prueba = condicion.subs(x, a + lado * paso)
            if prueba == sp.true:
                return rama_lateral(rama, x, a, lado)
            if prueba != sp.false:
                raise ValueError('no se pudo decidir la rama lateral')
        return sp.nan
    return expr.replace(lambda v: isinstance(v, sp.Piecewise), elegir)

def limite_lateral(expr, x, a, lado):
    rama = rama_lateral(expr, x, a, lado)
    return sp.limit(rama, x, a, dir='-' if lado < 0 else '+')

def analizar_punto(original, dibujable, x, a, *, derivada=False):
    resultado = {'x': numero_real(a), 'estado': 'no_verificable', 'valor': None,
                 'izquierda': None, 'derecha': None, 'limite': None}
    try:
        original_a = valor_original(original, x, a)
        y = numero_real(original_a)
        if derivada:
            izquierda = limite_lateral((original - original_a) / (x - a), x, a, -1) if y is not None else sp.nan
            derecha = limite_lateral((original - original_a) / (x - a), x, a, 1) if y is not None else sp.nan
            li, ld = numero_real(izquierda), numero_real(derecha)
            existe = y is not None and li is not None and ld is not None and sp.simplify(izquierda - derecha) == 0
            resultado['valor'] = li if existe else None
            resultado['estado'] = 'no_verificable' if izquierda.has(sp.Limit) or derecha.has(sp.Limit) else 'definida' if existe else 'no_derivable'
        else:
            resultado['valor'] = y
            resultado['estado'] = 'definida' if y is not None else 'no_definida'
        izq = limite_lateral(dibujable, x, a, -1)
        der = limite_lateral(dibujable, x, a, 1)
        resultado.update(izquierda=numero_real(izq), derecha=numero_real(der))
        if izq in (sp.oo, -sp.oo) or der in (sp.oo, -sp.oo):
            resultado['tipo'] = 'asintota'
        elif resultado['izquierda'] is not None and resultado['derecha'] is not None:
            if sp.simplify(izq - der) == 0:
                resultado['limite'] = resultado['izquierda']
                resultado['tipo'] = 'continuo' if resultado['valor'] == resultado['limite'] else 'hueco'
            else:
                resultado['tipo'] = 'salto'
        else:
            resultado['tipo'] = 'frontera_o_no_convergente'
    except (ValueError, TypeError, NotImplementedError, RecursionError):
        resultado['tipo'] = 'no_verificable'
    return resultado

def informacion_dominio(original, dibujable, x, *, destino=None, derivada=False):
    puntos = fronteras(original, x)
    if destino is not None and numero_real(destino) is not None and destino not in puntos:
        puntos.insert(0, destino)
    analisis = [analizar_punto(original, dibujable, x, a, derivada=derivada) for a in puntos]
    return {'puntos': analisis, 'alcance': 'Fronteras finitas encontradas y punto solicitado; el dominio original se conserva al evaluar.'}
