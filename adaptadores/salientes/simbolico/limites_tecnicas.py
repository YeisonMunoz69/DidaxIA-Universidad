from __future__ import annotations

import sympy as sp
from sympy import Symbol

Paso = dict[str, str]


def _paso(tipo: str, formula: str, regla: str) -> Paso:
    return {"tipo": tipo, "latex": formula, "regla": regla}

def partes_racionales(expr: sp.Expr) -> tuple[sp.Expr, sp.Expr]:
    numerador, denominador = sp.fraction(expr)
    if denominador == 1 and expr.is_Add:
        numerador, denominador = sp.fraction(sp.together(expr))
    return sp.factor(numerador), sp.factor(denominador)

def valor_directo_finito(expr: sp.Expr, variable: Symbol, destino: sp.Expr) -> sp.Expr | None:
    if destino in (sp.oo, -sp.oo):
        return None
    valor = sp.simplify(expr.subs(variable, destino))
    if valor in (sp.nan, sp.zoo, sp.oo, -sp.oo) or valor.is_infinite:
        return None
    return valor if valor.is_number else None

def _conjugado_del_radical(numerador: sp.Expr) -> sp.Expr | None:
    if not numerador.is_Add:
        return None
    radical = next(
        (t for t in numerador.args if t.is_Pow and t.exp == sp.Rational(1, 2)), None
    )
    if radical is None:
        return None
    resto = sp.expand(numerador - radical)
    return sp.expand(radical - resto)

def pasos_de_factorizacion(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr
) -> tuple[list[Paso], sp.Expr | None]:

    numerador, denominador = partes_racionales(expr)
    factorizado = sp.factor(numerador) / sp.factor(denominador)
    pasos: list[Paso] = []

    if factorizado != expr:
        pasos.append(_paso(
            "tecnica",
            rf"{sp.latex(expr)} = \dfrac{{{sp.latex(sp.factor(numerador))}}}"
            rf"{{{sp.latex(sp.factor(denominador))}}}",
            "Factorizar numerador y denominador",
        ))

    cancelado = sp.cancel(factorizado)
    if cancelado == expr:
        return pasos, None

    pasos.append(_paso(
        "simplificacion",
        rf"\dfrac{{{sp.latex(sp.factor(numerador))}}}"
        rf"{{{sp.latex(sp.factor(denominador))}}} = {sp.latex(cancelado)}",
        "Simplificar factores comunes",
    ))

    evaluado = valor_directo_finito(cancelado, variable, destino)
    if evaluado is not None:
        pasos.append(_paso(
            "sustitucion_directa",
            rf"{sp.latex(cancelado)}\bigg|_{{{variable}={sp.latex(destino)}}} = {sp.latex(evaluado)}",
            "Evaluar la expresión simplificada",
        ))
    return pasos, evaluado

def pasos_de_racionalizacion(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr
) -> tuple[list[Paso], sp.Expr | None]:
    numerador, denominador = partes_racionales(expr)
    conjugado = _conjugado_del_radical(numerador)
    if conjugado is None:
        return [], None

    racionalizado = sp.cancel(
        sp.expand(numerador * conjugado) / sp.expand(denominador * conjugado)
    )
    if racionalizado == expr:
        return [], None

    pasos = [
        _paso(
            "tecnica",
            rf"\dfrac{{{sp.latex(numerador)}}}{{{sp.latex(denominador)}}}"
            rf"\cdot \dfrac{{{sp.latex(conjugado)}}}{{{sp.latex(conjugado)}}}",
            "Multiplicar por el conjugado",
        ),
        _paso("simplificacion", rf"= {sp.latex(racionalizado)}", "Simplificar usando diferencia de cuadrados"),
    ]
    evaluado = valor_directo_finito(racionalizado, variable, destino)
    if evaluado is not None:
        pasos.append(_paso(
            "sustitucion_directa",
            rf"{sp.latex(racionalizado)}\bigg|_{{{variable}={sp.latex(destino)}}} = {sp.latex(evaluado)}",
            "Evaluar después de racionalizar",
        ))
    return pasos, evaluado

def pasos_de_lhopital(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None = None
) -> list[Paso]:
    numerador, denominador = sp.fraction(sp.together(expr))
    num_actual, den_actual = numerador, denominador
    pasos: list[Paso] = []

    for _ in range(3):
        num_siguiente = sp.diff(num_actual, variable)
        den_siguiente = sp.diff(den_actual, variable)
        if den_siguiente == 0:
            break
        expr_siguiente = sp.cancel(num_siguiente / den_siguiente)
        pasos.append(_paso(
            "tecnica",
            rf"\dfrac{{d}}{{d{variable}}}\left[{sp.latex(num_actual)}\right]"
            rf"\Big/\dfrac{{d}}{{d{variable}}}\left[{sp.latex(den_actual)}\right]"
            rf" = {sp.latex(expr_siguiente)}",
            "Aplicar la regla de L'Hôpital",
        ))

        if destino not in (sp.oo, -sp.oo):
            valor = sp.simplify(expr_siguiente.subs(variable, destino))
            if valor.is_number and not valor.is_infinite and valor not in (sp.nan, sp.zoo):
                pasos.append(_paso(
                    "sustitucion_directa",
                    rf"{sp.latex(expr_siguiente)}\bigg|_{{{variable}={sp.latex(destino)}}} = {sp.latex(valor)}",
                    "Evaluar después de aplicar L'Hôpital",
                ))
                break

        num_actual, den_actual = num_siguiente, den_siguiente
    return pasos

def pasos_de_dominancia(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None = None
) -> list[Paso]:

    numerador, denominador = partes_racionales(expr)
    try:
        grado_num = sp.Poly(numerador, variable).degree()
        grado_den = sp.Poly(denominador, variable).degree()
    except sp.PolynomialError:
        return []

    dominante = variable ** max(grado_num, grado_den)
    num_normalizado = sp.expand(numerador / dominante)
    den_normalizado = sp.expand(denominador / dominante)
    normalizado = sp.cancel(num_normalizado / den_normalizado)

    pasos = [
        _paso(
            "tecnica",
            rf"\deg(N)={grado_num},\ \deg(D)={grado_den};\quad \text{{ dividir por }} {sp.latex(dominante)}",
            "Comparar términos dominantes al infinito",
        ),
        _paso(
            "simplificacion",
            rf"\lim_{{{variable}\to {sp.latex(destino)}}}"
            rf"\dfrac{{{sp.latex(num_normalizado)}}}{{{sp.latex(den_normalizado)}}}",
            "Eliminar los términos que tienden a cero",
        ),
    ]
    evaluado = sp.limit(normalizado, variable, destino, dir=direccion) if direccion else sp.limit(normalizado, variable, destino)
    pasos.append(_paso("sustitucion_directa", rf"\Rightarrow {sp.latex(evaluado)}", "Evaluar el cociente de términos dominantes"))
    return pasos

def forma_de_producto(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr
) -> tuple[str | None, sp.Expr | None, sp.Expr | None]:

    if not expr.is_Mul or destino in (sp.oo, -sp.oo):
        return None, None, None

    factor_cero = factor_infinito = None
    for factor in expr.args:
        valor = sp.simplify(factor.subs(variable, destino))
        if valor == 0:
            factor_cero = factor
        elif valor in (sp.oo, -sp.oo, sp.zoo) or valor.is_infinite:
            factor_infinito = factor
    if factor_cero is not None and factor_infinito is not None:
        return "0*inf", factor_cero, factor_infinito
    return None, None, None

def pasos_de_producto_a_cociente(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr
) -> tuple[list[Paso], sp.Expr | None]:
    forma, factor_cero, factor_infinito = forma_de_producto(expr, variable, destino)
    if forma is None:
        return [], None

    resto = sp.cancel(expr / (factor_cero * factor_infinito))
    numerador = resto * factor_cero
    denominador = 1 / factor_infinito
    return [
        _paso(
            "tecnica",
            rf"{sp.latex(expr)} = \dfrac{{{sp.latex(numerador)}}}{{1/{sp.latex(factor_infinito)}}}",
            "Convertir la forma 0·∞ en un cociente 0/0",
        ),
        _paso(
            "tecnica",
            rf"\dfrac{{d}}{{d{variable}}}\left[{sp.latex(numerador)}\right]"
            rf"\Big/\dfrac{{d}}{{d{variable}}}\left[{sp.latex(denominador)}\right]"
            rf" = {sp.latex(sp.cancel(sp.diff(numerador, variable) / sp.diff(denominador, variable)))}",
            "Aplicar L'Hôpital después de convertir el producto",
        ),
    ], None

def paso_de_potencia_indeterminada(
    expr: sp.Expr, variable: Symbol, destino: sp.Expr, direccion: str | None = None
) -> list[Paso]:

    if not expr.is_Pow:
        return []
    base, exponente = expr.args
    if not base.has(variable) and not exponente.has(variable):
        return []

    limite_base = sp.limit(base, variable, destino, dir=direccion) if direccion else sp.limit(base, variable, destino)
    limite_exp = sp.limit(exponente, variable, destino, dir=direccion) if direccion else sp.limit(exponente, variable, destino)
    if limite_base not in (0, 1, sp.oo, -sp.oo) or limite_exp not in (0, sp.oo, -sp.oo):
        return []

    return [
        _paso(
            "tecnica",
            rf"\ln L = \lim_{{{variable}\to {sp.latex(destino)}}} {sp.latex(exponente)}\,\ln\left({sp.latex(base)}\right)",
            "Aplicar la técnica logarítmica para una potencia indeterminada",
        ),
        _paso(
            "nota",
            rf"\text{{La forma detectada es }} {sp.latex(limite_base)}^{{{sp.latex(limite_exp)}}}.",
            "Transformar la potencia en un producto mediante logaritmos",
        ),
    ]
