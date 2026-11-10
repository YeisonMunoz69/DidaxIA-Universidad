"""Subobjetivos verificables derivados del AST, no de ejercicios de ejemplo."""
import hashlib

import sympy as sp

from adaptadores.salientes.simbolico.analizador import analizar


def _parciales(tipo, expr, variable):
    if tipo == "valor":
        return [("valor", n) for n in sp.postorder_traversal(expr)
                if n != expr and not n.is_Atom and not n.free_symbols][:7]
    if tipo == "derivada":
        return [("derivada", n) for n in sp.postorder_traversal(expr)
                if n != expr and sp.Symbol(variable) in n.free_symbols and not n.is_Atom][:3]
    return []


def objetivos(activo):
    tipo, texto = activo["tipo"], activo["expresion"]
    variable = activo.get("variable", "x")
    salida = []

    def agregar(operacion, expr, alcance):
        formula = str(expr).replace("**", "^")
        identidad = hashlib.sha256(f"{operacion}:{variable}:{formula}:{alcance}".encode()).hexdigest()[:20]
        if identidad not in {p["id"] for p in salida}:
            salida.append(dict(id=identidad, tipo=operacion, expresion=formula, variable=variable,
                               alcance=alcance, respuesta_esperada="expresion"))

    try:
        expr = analizar(texto, variable, evaluar=False)
        if sp.count_ops(expr) > 80:
            return []
        # Una cancelación algebraica puede evitar pasos artificiales sobre un
        # factor recíproco; la tarea final conserva la expresión y su dominio.
        simplificada = sp.cancel(expr) if tipo in ('derivada', 'valor_derivada') and expr.is_rational_function() else expr
        base = simplificada if sp.count_ops(simplificada) < sp.count_ops(expr) else expr
        for operacion, nodo in (_parciales(tipo, base, variable) if activo.get("orden", 1) == 1 else []):
            agregar(operacion, nodo, "parcial")
        agregar(tipo, texto, "final")
        if salida:
            salida[-1]["orden"] = activo.get("orden", 1)
        return salida[:8]
    except (ValueError, TypeError, AttributeError):
        return []


def citas_relacionadas(datos):
    """Permitir subexpresiones y sustituciones de la tarea, sin acreditar resultados."""
    activo, citas = datos
    try:
        variable = activo.get('variable', 'x')
        expr = analizar(activo['expresion'], variable, evaluar=False)
        if sp.count_ops(expr) > 80 or len(citas) > 12:
            return False
        arboles = [expr]
        punto = None
        if activo.get('tipo') == 'valor_derivada':
            # Evaluar una derivada admite citar su fórmula, aunque ésta no
            # aparezca como subárbol de la función original. No acredita nada.
            derivada = sp.diff(expr, sp.Symbol(variable), activo.get('orden', 1))
            arboles.append(derivada)
            punto = analizar(activo['destino'], variable)
            arboles.append(derivada.subs(sp.Symbol(variable), punto))
        if activo.get('tipo') == 'limite':
            from adaptadores.salientes.simbolico.limites import analizar_destino_del_limite

            destino, _ = analizar_destino_del_limite(activo['destino'], variable)
            if destino.is_finite:
                arboles.append(expr.subs(sp.Symbol(variable), destino))
            if expr.is_rational_function():
                arboles.append(sp.cancel(expr))
        permitidas = {sp.srepr(analizar(str(n), variable)) for arbol in arboles
                      for n in sp.preorder_traversal(arbol) if n not in (sp.nan, sp.zoo)}
        return all(_cita_relacionada(cita, variable, punto, permitidas) for cita in citas)
    except (ValueError, TypeError, AttributeError):
        return False


def _cita_relacionada(cita, variable, punto, permitidas):
    if punto is not None and '=' in cita:
        izq, _, der = cita.partition('=')
        return izq.strip() == variable and analizar(der, variable) == punto
    return sp.srepr(analizar(cita, variable)) in permitidas


def referencia_transformada(datos):
    """Logaritmos reales en el dominio positivo, sin expandir ramas a la fuerza."""
    activo, transformacion = datos
    try:
        nombre = activo.get('variable', 'x')
        variable = sp.Symbol(nombre)
        positivo = sp.Symbol(nombre, positive=True)
        expr = analizar(activo['expresion'], nombre).subs(variable, positivo)
        if sp.count_ops(expr) > 80 or expr.is_positive is not True:
            return None
        log = sp.expand_log(sp.log(expr))
        if isinstance(transformacion, dict):
            ref = _derivada_del_ultimo_termino(transformacion, log, nombre, positivo)
            if ref is None:
                return None
        else:
            ref = log if transformacion == 'log' else sp.diff(log, positivo)
        return dict(expresion=str(ref.subs(positivo, variable)).replace('**', '^'),
                    variable=nombre, tipo='equivalencia', dominio=f'{nombre}>0 y función positiva')
    except (ValueError, TypeError, AttributeError):
        return None


def _derivada_del_ultimo_termino(transformacion, referencia, nombre, positivo):
    if transformacion.get('tipo') != 'derivada_termino_log':
        return None
    # El orden procede de la expansión escrita y acreditada, no del orden
    # canónico con que SymPy reorganiza las sumas.
    fuente = analizar(transformacion['fuente'], nombre, evaluar=False)
    if not isinstance(fuente, sp.Add) or sp.count_ops(fuente) > 80:
        return None
    original = sp.Symbol(nombre)
    if sp.simplify(fuente.subs(original, positivo) - referencia) != 0:
        return None
    return sp.diff(fuente.args[-1].subs(original, positivo), positivo)
