from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from sympy import Symbol

from adaptadores.salientes.simbolico.analizador import analizar
from adaptadores.salientes.simbolico.limites_tecnicas import (
    Paso,
    forma_de_producto,
    partes_racionales,
    paso_de_potencia_indeterminada,
    pasos_de_dominancia,
    pasos_de_factorizacion,
    pasos_de_lhopital,
    pasos_de_producto_a_cociente,
    pasos_de_racionalizacion,
)


@dataclass(frozen=True)
class _DeteccionDeForma:

    forma: str | None
    forma_potencia: str | None
    forma_producto: str | None

@dataclass(frozen=True)
class EvaluacionDeLimite:

    pasos: list[Paso]
    resultado: sp.Expr

class LimiteBilateralInexistente(ValueError):

    def __init__(self, izquierdo: sp.Expr, derecho: sp.Expr) -> None:
        super().__init__("el límite bilateral no existe")
        self.izquierdo = izquierdo
        self.derecho = derecho

def _paso(tipo: str, formula: str, regla: str) -> Paso:
    return {"tipo": tipo, "latex": formula, "regla": regla}

def analizar_destino_del_limite(valor: str, variable: str = "x") -> tuple[sp.Expr, str | None]:
    normalizado = (valor or "0").strip().replace("∞", "oo").replace("inf", "oo") or "0"

    direccion: str | None = None
    if normalizado.endswith(("+", "-")) and normalizado not in ("+", "-"):
        direccion = normalizado[-1]
        normalizado = normalizado[:-1].strip()

    destino = analizar(normalizado, variable=variable)
    inesperados = destino.free_symbols - {sp.Symbol(variable)}
    if inesperados:
        nombres = ", ".join(sorted(str(s) for s in inesperados))
        raise ValueError(f"el destino del límite contiene variables no permitidas: {nombres}")
    if destino.has(sp.Symbol(variable)):
        raise ValueError("el destino del límite no puede depender de la variable de estudio")
    return destino, direccion

def _es_infinito(valor: sp.Expr) -> bool:
    return bool(valor in (sp.oo, -sp.oo, sp.zoo) or valor.is_infinite)

def evaluar_valor_del_limite(expr: sp.Expr, variable: Symbol, destino: sp.Expr,
                             direccion: str | None) -> sp.Expr:

    lado = direccion or ("+-" if destino.is_finite else "+")
    try:
        resultado = sp.limit(expr, variable, destino, dir=lado)
    except ValueError as e:
        if lado != "+-":
            raise
        izquierdo = sp.limit(expr, variable, destino, dir="-")
        derecho = sp.limit(expr, variable, destino, dir="+")
        raise LimiteBilateralInexistente(izquierdo, derecho) from e
    if lado == "+-" and (resultado in (sp.zoo, sp.nan) or not resultado.is_number):
        izquierdo = sp.limit(expr, variable, destino, dir="-")
        derecho = sp.limit(expr, variable, destino, dir="+")
        raise LimiteBilateralInexistente(izquierdo, derecho)
    if resultado in (sp.zoo, sp.nan):
        raise ValueError("el límite lateral no converge")
    return resultado

def _forma_directa(expr: sp.Expr, variable: Symbol, destino: sp.Expr) -> tuple[str | None, sp.Expr | None]:
    if destino in (sp.oo, -sp.oo):
        return None, None

    numerador, denominador = partes_racionales(expr)
    valor_num = sp.simplify(numerador.subs(variable, destino))
    valor_den = sp.simplify(denominador.subs(variable, destino))

    if valor_num == 0 and valor_den == 0:
        return "0/0", sp.nan
    if valor_den == 0 and valor_num != 0:
        return "nonzero/0", sp.zoo

    directo = sp.simplify(expr.subs(variable, destino))
    if directo in (sp.nan, sp.zoo) or directo.is_infinite:
        return "undefined", directo
    if directo.is_number:
        return None, directo
    return None, None

def _forma_de_potencia(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None
) -> str | None:

    if not expr.is_Pow:
        return None
    base, exponente = expr.args
    try:
        if destino in (sp.oo, -sp.oo):
            valor_base = sp.limit(base, variable, destino, dir=direccion) if direccion else sp.limit(base, variable, destino)
            valor_exp = sp.limit(exponente, variable, destino, dir=direccion) if direccion else sp.limit(exponente, variable, destino)
        else:
            valor_base = base.subs(variable, destino)
            valor_exp = exponente.subs(variable, destino)
    except Exception:
        return None

    if valor_base == 1 and _es_infinito(valor_exp):
        return "1^inf"
    if valor_base == 0 and valor_exp == 0:
        return "0^0"
    if _es_infinito(valor_base) and valor_exp == 0:
        return "inf^0"
    return None

def _forma_detectada(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None
) -> tuple[_DeteccionDeForma, sp.Expr | None]:

    forma_potencia = _forma_de_potencia(expr, variable, destino, direccion)
    forma, directo = _forma_directa(expr, variable, destino)
    forma_producto, _, _ = forma_de_producto(expr, variable, destino)
    if forma_potencia is not None:
        return _DeteccionDeForma(forma_potencia, forma_potencia, forma_producto), sp.nan
    if forma_producto is not None and forma != "0/0":
        return _DeteccionDeForma(forma_producto, forma_potencia, forma_producto), sp.nan
    return _DeteccionDeForma(forma, forma_potencia, forma_producto), directo

def _pasos_de_la_tecnica(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None, deteccion: _DeteccionDeForma
) -> list[Paso]:

    if deteccion.forma_potencia is not None:
        return paso_de_potencia_indeterminada(expr, variable, destino, direccion)
    if destino in (sp.oo, -sp.oo):
        return pasos_de_dominancia(expr, variable, destino, direccion)
    if deteccion.forma_producto is not None and deteccion.forma == deteccion.forma_producto:
        pasos, _ = pasos_de_producto_a_cociente(expr, variable, destino)
        return pasos
    if deteccion.forma == "0/0":
        return _pasos_de_forma_cero_sobre_cero(expr, variable, destino, direccion)
    if expr.is_Pow:
        return paso_de_potencia_indeterminada(expr, variable, destino, direccion)
    return []

def _pasos_de_forma_cero_sobre_cero(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None
) -> list[Paso]:

    pasos, resuelto = pasos_de_factorizacion(expr, variable, destino)
    if resuelto is None:
        pasos, resuelto = pasos_de_racionalizacion(expr, variable, destino)
    if resuelto is not None:
        return pasos
    if not pasos:
        return pasos_de_lhopital(expr, variable, destino, direccion)
    if not any("L'Hôpital" in p["regla"] for p in pasos):
        return pasos + pasos_de_lhopital(expr, variable, destino, direccion)
    return pasos

def evaluar_limite_con_pasos(expr: sp.Expr, variable: Symbol, valor: str) -> EvaluacionDeLimite:
    destino, direccion = analizar_destino_del_limite(valor, str(variable))
    latex_original = sp.latex(expr)
    latex_destino = sp.latex(destino) + (rf"^{{{direccion}}}" if direccion else "")

    pasos: list[Paso] = [_paso(
        "inicio", rf"\lim_{{{variable}\to {latex_destino}}}\left[{latex_original}\right]", "Planteamiento del límite"
    )]

    deteccion, directo = _forma_detectada(expr, variable, destino, direccion)

    if deteccion.forma is None and directo is not None:
        pasos.extend([
            _paso("sustitucion_directa", rf"{variable}={latex_destino}\Rightarrow {sp.latex(directo)}", "Sustitución directa: no aparece una indeterminación"),
            _paso("resultado_final", rf"= {sp.latex(directo)}", "Resultado del límite"),
        ])
        resultado = directo
    else:
        forma_mostrada_de = deteccion.forma or "indeterminada"
        forma_mostrada = {"nonzero/0": "a/0", "undefined": "indefinida"}.get(forma_mostrada_de, forma_mostrada_de)
        pasos.append(_paso("indeterminacion", rf"{variable}={latex_destino}\Rightarrow {forma_mostrada}", f"Forma detectada: {forma_mostrada}"))

        resultado = evaluar_valor_del_limite(expr, variable, destino, direccion)
        pasos.extend(_pasos_de_la_tecnica(expr, variable, destino, direccion, deteccion))
        pasos.append(_paso("resultado_final", rf"= {sp.latex(resultado)}", "Resultado del límite"))

    pasos.append(_paso(
        "verificacion",
        rf"\lim_{{{variable}\to {latex_destino}}}\left[{latex_original}\right] = {sp.latex(resultado)}",
        "Resultado final verificado por SymPy",
    ))
    return EvaluacionDeLimite(pasos=pasos, resultado=resultado)
