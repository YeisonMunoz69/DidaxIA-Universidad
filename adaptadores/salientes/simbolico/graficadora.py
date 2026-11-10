from __future__ import annotations

import math
import re

import sympy as sp

from adaptadores.salientes.simbolico.analizador import analizar
from adaptadores.salientes.simbolico.dominio_grafica import informacion_dominio, numero_real
from adaptadores.salientes.simbolico.limites import analizar_destino_del_limite
from adaptadores.salientes.simbolico.notacion_grafica import _grupo, normalizar_funcion_grafica
from adaptadores.salientes.simbolico.presentacion import expr_to_js

VARIABLES = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZθ")
TIPOS = frozenset({"funcion", "derivada", "limite"})
MAX_FUNCION_CARACTERES = 2000
MAX_FUNCION_OPERACIONES = 160


def preparar_curvas(solicitudes: list[dict], *, estudiar_dominio=False) -> list[dict]:
    if not isinstance(solicitudes, list) or not 1 <= len(solicitudes) <= 4:
        raise ValueError("elige entre una y cuatro funciones")

    return [_preparar_una(solicitud, indice, estudiar_dominio) for indice, solicitud in enumerate(solicitudes, 1)]

def _destino_de(solicitud: dict, variable: str) -> tuple[str, float | None]:
    destino = str(solicitud.get("destino") or "").strip()
    if not destino or len(destino) > 24:
        raise ValueError("indica el punto al que tiende la variable")
    punto, _direccion = analizar_destino_del_limite(destino, variable)
    if punto.is_real and punto.is_finite:
        candidato = float(punto.evalf())
        if math.isfinite(candidato):
            return destino, candidato
    return destino, None

def _entrada_grafica(fuente, tipo, variable, solicitud):
    entrada = fuente.strip('$').strip()
    destino_escrito = None
    if tipo == 'limite':
        prefijo = re.match(r'\\lim\s*(?:\\limits\s*)?_\s*', entrada)
        if prefijo:
            subindice, fin = _grupo(entrada, prefijo.end(), '{', '}')
            operador = re.fullmatch(r'\s*([a-zA-Zθ])\s*\\(?:to|rightarrow)\s*(.+)', subindice)
            if not operador or operador[1] != variable:
                raise ValueError('la variable del límite no coincide con la elegida')
            destino_escrito = operador[2].replace(r'\infty', 'oo').replace(r'\pi','pi')
            destino_escrito = re.sub(r'\^\s*(?:\{\s*([+-])\s*\}|([+-]))\s*$', lambda m: m[1] or m[2], destino_escrito)
            entrada = entrada[fin:]
        else:
            operador = re.match(r'lim\s*(?:' + re.escape(variable) + r'\s*)?(?:-+>|→)\s*(\S+)\s+(?:de\s+)?(.+)', entrada, re.I | re.S)
            if operador:
                destino_escrito, entrada = operador[1], operador[2]
    if destino_escrito is not None:
        if solicitud.get('destino'):
            indicado, lado = analizar_destino_del_limite(str(solicitud['destino']), variable)
            escrito, lado_escrito = analizar_destino_del_limite(destino_escrito, variable)
            if indicado != escrito or lado != lado_escrito:
                raise ValueError('el destino escrito no coincide con el campo Tiende a')
        solicitud['destino'] = destino_escrito
    if tipo == 'derivada':
        entrada = re.sub(r'^\\frac\{d\}\{d' + re.escape(variable) + r'\}\s*', '', entrada)
    return normalizar_funcion_grafica(entrada)

def _resultado_limite(expresion, simbolo, punto, direccion, dominio):
    if numero_real(punto) is not None:
        evidencia = next(p for p in dominio['puntos'] if p['x'] == numero_real(punto))
        valor = evidencia['derecha' if direccion == '+' else 'izquierda'] if direccion else evidencia['limite']
        return {'valor': valor, 'estado': evidencia['tipo'], 'direccion': direccion}
    try:
        valor = sp.limit(expresion, simbolo, punto)
        return {'valor': numero_real(valor), 'estado': str(valor), 'direccion': direccion}
    except (ValueError, NotImplementedError):
        return {'valor': None, 'estado': 'no_verificable', 'direccion': direccion}

def _preparar_una(solicitud: dict, indice: int, estudiar_dominio: bool) -> dict:
    if not isinstance(solicitud, dict):
        raise ValueError(f"la función {indice} no es válida")
    fuente = str(solicitud.get("expresion") or "").strip()
    variable = str(solicitud.get("variable") or "x").strip()
    tipo = str(solicitud.get("tipo") or "funcion").strip()
    if variable not in VARIABLES or tipo not in TIPOS:
        raise ValueError(f"la función {indice} tiene tipo o variable no admitidos")
    maximo = MAX_FUNCION_CARACTERES
    if not fuente or len(fuente) > maximo:
        raise ValueError(f"la función {indice} debe tener entre 1 y {maximo} caracteres")

    try:
        solicitud = dict(solicitud)
        entrada = _entrada_grafica(fuente, tipo, variable, solicitud)
        original = analizar(entrada, variable, evaluar=False, real=True)
        expresion = analizar(entrada, variable, real=True)
        simbolo = sp.Symbol(variable, real=True)
        if expresion.free_symbols - {simbolo}:
            raise ValueError("contiene otras variables")
        max_operaciones = MAX_FUNCION_OPERACIONES
        if sp.count_ops(expresion) > max_operaciones:
            raise ValueError(f"supera {max_operaciones} operaciones para una gráfica interactiva")
        destino, destino_numero = _destino_de(solicitud, variable) if tipo == "limite" or (tipo == 'derivada' and solicitud.get('destino')) else (None, None)
        dibujable = sp.diff(expresion, simbolo) if tipo == "derivada" else expresion
        if dibujable.has(sp.Derivative, sp.DiracDelta):
            raise ValueError('la derivada no tiene una representación ordinaria verificable')
        js = expr_to_js(dibujable.xreplace({simbolo: sp.Symbol("x")}))

        original_js = re.sub(r'\b' + re.escape(variable) + r'\b', 'x', expr_to_js(original))
        punto, direccion = analizar_destino_del_limite(destino, variable) if destino else (None, None)
        dominio = informacion_dominio(original, dibujable, simbolo, destino=punto, derivada=tipo == 'derivada') if estudiar_dominio else {'puntos': [], 'alcance': 'No se realizó el análisis opcional de puntos especiales; se conserva el evaluador original.'}
        resultado_limite = None
        if tipo == 'limite' and estudiar_dominio:
            resultado_limite = _resultado_limite(expresion, simbolo, punto, direccion, dominio)
        if not js:
            raise ValueError("no se puede representar en el plano")
    except Exception as error:
        raise ValueError(f"función {indice}: {error}") from error

    return {
        "funcion_js": js,
        "dominio_js": original_js,
        "dominio": dominio,
        "resultado_limite": resultado_limite,
        "expresion": fuente,
        "tipo": tipo,
        "variable": variable,
        "limite_destino": destino if tipo == 'limite' else None,
        "limite_x": destino_numero if tipo == 'limite' else None,
        "punto_x": destino_numero if tipo == 'derivada' else None,
    }
