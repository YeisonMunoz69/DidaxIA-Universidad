"""Retroalimentación optativa de propuestas que el CAS pudo refutar."""

import re
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.filtros.intento import propuesta_en_el_turno
from dominio.modelo.respuesta import Afirmacion, ExpresionCitada, RespuestaGenerada
from dominio.pedagogia.politica import INVALIDA


def _orientacion_derivada(pre, expresion):
    regla = pre.paso_intermedio_regla or pre.regla_critica or ""
    if re.search(r"log\s*\(.+,\s*\d+\s*\)", expresion):
        return "En un logaritmo de base distinta de la natural también debes incluir el factor de cambio de base, además de la derivada de la función interior."
    if "cociente" in regla:
        return "Aplica la regla del cociente: derivada del numerador por el denominador, menos el numerador por la derivada del denominador; divide todo por el denominador al cuadrado. Derivar arriba y abajo por separado no aplica esa regla."
    if "producto" in regla:
        return "Aplica la regla del producto: derivada del primer factor por el segundo sin derivar, más el primero sin derivar por la derivada del segundo. No basta multiplicar las dos derivadas."
    if "cadena" in regla:
        return "Deriva la función exterior, conserva su argumento y multiplica por la derivada de la función interior. Revisa que ese último factor esté presente."
    if "potencia" in regla:
        return "La regla de la potencia con exponente constante usa ese exponente como factor y lo reduce en una unidad. Si también el exponente depende de la variable, necesitas derivación logarítmica."
    return "Revisa qué regla de derivación corresponde a la estructura de la función."


class FiltroRetroalimentacion(Filtro):
    nombre = "preparación de retroalimentación comprobada"
    ruta = "caliente"

    def __init__(self, simbolico):
        self.simbolico = simbolico

    def _procesar(self, ctx):
        if ctx.paso_pendiente and ctx.paso_pendiente.get("veredicto") in ("valida", "invalida"):
            return self._retroalimentar_paso(ctx)
        pre, activo = ctx.precomputo, ctx.ejercicio_activo or {}
        propuesta = (ctx.continuidad or {}).get("propuesta") or propuesta_en_el_turno(ctx.texto_estudiante)
        if (ctx.veredicto_del_intento != INVALIDA or not propuesta or not activo
                or pre is None or not pre.ok or not pre.resultado_corriente):
            return ctx, {"preparada": False, "motivo": "sin propuesta refutada y referencia verificable"}
        variable = activo.get("variable", "x")
        expresion = activo.get("expresion", "")
        if activo.get("tipo") == "limite":
            izquierda = f"lim {variable}->{activo.get('destino', '')} ({expresion})"
            orientacion = "En un límite se comprueba el comportamiento al acercarse al punto; la sustitución directa puede necesitar una transformación previa."
        elif activo.get("tipo") == "derivada":
            orden = activo.get("orden", 1)
            izquierda = f"d^{orden}/d{variable}^{orden} ({expresion})" if orden > 1 else f"d/d{variable} ({expresion})"
            orientacion = _orientacion_derivada(pre, expresion)
        elif activo.get("tipo") in ("valor", "valor_derivada"):
            izquierda = pre.expresion_fuente or (expresion if activo.get("tipo") == "valor" else "")
            if not izquierda:
                return ctx, {"preparada": False, "motivo": "sin expresión evaluada verificable"}
            orientacion = "Revisa las operaciones y el orden en que las realizaste."
        else:
            return ctx, {"preparada": False, "motivo": "familia matemática sin soporte"}
        base = RespuestaGenerada(
            narracion=("La propuesta {{c_feedback}} no coincide con el resultado de este ejercicio. "
                       "Al comprobarlo se obtiene {{a_feedback}}. " + orientacion
                       + " Podemos revisar tu procedimiento para localizar la diferencia."),
            afirmaciones=(Afirmacion("a_feedback", izquierda, "=", pre.resultado_corriente),),
            citadas=(ExpresionCitada("c_feedback", propuesta),), nivel_divulgacion=2,
        )
        if base.problemas() or not self.simbolico.verificar(base.bloques()).aprobada:
            return ctx, {"preparada": False, "motivo": "la referencia no superó contrato y verificación"}
        return replace(ctx, retroalimentacion_del_intento=base, nivel_divulgacion=2), {
            "preparada": True, "propuesta": propuesta, "referencia": pre.resultado_corriente,
            "alcance": "comparación del resultado; no diagnóstico del procedimiento",
        }

    def _retroalimentar_paso(self, ctx):
        paso = ctx.paso_pendiente
        izquierda = (f"d/d{paso['variable']} ({paso['expresion']})"
                     if paso['tipo'] == 'derivada' else paso['expresion'])
        if paso.get('negada'):
            inicio = ("La afirmación de que el resultado de este paso es distinto de {{c_paso}} "
                      + ("es compatible con la comprobación. " if paso['veredicto'] == 'valida' else "no se cumple. "))
        else:
            inicio = ("Tu respuesta {{c_paso}} "
                      + ("es correcta para el paso preguntado. " if paso['veredicto'] == 'valida' else "no coincide con este paso. "))
        if paso.get('dominio'):
            inicio = "En el dominio positivo de la función, " + inicio[0].lower() + inicio[1:]
        cierre = ("Conserva este paso y continúa con la operación restante del ejercicio. "
                  "El resultado final todavía no se ha comprobado."
                  if paso['veredicto'] == 'valida' else "Revisa este paso antes de continuar.")
        base = RespuestaGenerada(
            narracion=inicio + "La comprobación es {{a_paso}}. " + cierre,
            afirmaciones=(Afirmacion("a_paso", izquierda, "=", paso['resultado_corriente']),),
            citadas=(ExpresionCitada("c_paso", paso['propuesta']),), nivel_divulgacion=2,
        )
        if base.problemas() or not self.simbolico.verificar(base.bloques()).aprobada:
            return ctx, {"preparada": False, "motivo": "el paso no superó la verificación de salida"}
        return replace(ctx, retroalimentacion_del_intento=base, nivel_divulgacion=2), {
            "preparada": True, "alcance": "paso_preguntado", "veredicto_del_paso": paso['veredicto'],
            "propuesta": paso['propuesta'], "referencia": paso['resultado_corriente'],
        }
