"""
estrategia.py — Filtro 6.9 · qué clase de respuesta es este turno
=====================================================================

El filtro que faltaba. `ADR-001` §6.3 tenía arbitraje (6) y construcción del
prompt (7), y entre los dos **nadie decidía qué clase de respuesta era el
turno**: el 6 decidía cuánto revelar y qué intervención de `T6` tocaba, y el 7
ensamblaba siempre la misma forma —un repertorio de preguntas—. Por eso la
respuesta era socrática en 37 de los 43 turnos del banco congelado.

Qué hace, y qué deja a otros
-------------------------------
Reúne lo que los filtros anteriores decidieron en una `Situacion` —el contrato
de entrada de la política— y le pide la decisión a
`dominio/pedagogia/politica.py`. **Ninguna regla pedagógica vive aquí**: éste es
el sitio donde el contexto del turno se traduce al vocabulario de la política, y
la política es lo que una docente revisa.

Dónde va, y por qué no puede ir antes
----------------------------------------
Después del **6.75** (diagnóstico de dos niveles) y antes del **7** (prompt).
Las dos posiciones están forzadas: la política prefiere el diagnóstico a la
conjetura del motor simbólico, así que necesita que el 6.75 haya corrido; y el
prompt tiene que saber qué clase de respuesta pedir antes de escribir la
instrucción, igual que `ADR-014` §5.1 exige para el nivel de divulgación.

Lo que este filtro **no** hace, y es la mitad que importa
------------------------------------------------------------
**No decide cuánto se revela.** Eso es el filtro 6, y la política sólo lee su
resultado. La separación es lo que hace estructuralmente cierta la política F
de la fase: una señal conductual entra por `nivel_intervencion` y sale como
modificador o como primer paso, nunca como más matemática.


"""

from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales
from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import Intencion
from dominio.pedagogia.politica import Situacion, decidir


class FiltroEstrategia(Filtro):
    """Filtro 6.9 de la cadena, entre el diagnóstico y el prompt."""

    nombre = "selección de estrategia"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        situacion = Situacion(
            # Un contexto que no pasó por el filtro 2 no tiene intención, y eso
            # no puede producir una estrategia inventada: una `Intencion()` en
            # blanco es `ambigua` con origen `sin_resolver`, que la política
            # traduce a una aclaración. Es el mismo piso que `ADR-007` I4 fija.
            intencion=ctx.intencion_detalle or Intencion(),
            señales=ctx.señales or Señales(),
            nivel_divulgacion=ctx.nivel_divulgacion,
            alcance_divulgacion=ctx.alcance_divulgacion,
            nivel_intervencion=ctx.nivel_intervencion,
            diagnostico=ctx.diagnostico,
            concepciones_candidatas=(
                ctx.precomputo.concepciones_candidatas if ctx.precomputo is not None else ()
            ),
            veredicto_del_intento=ctx.veredicto_del_intento,
            hay_item_ofrecible=ctx.hay_item_ofrecible,
            sin_adaptacion=ctx.sin_adaptacion,
            estrategia_previa=ctx.estrategia_previa,
            hay_ejercicio_activo=bool(ctx.ejercicio_activo),
        )
        decision = decidir(situacion)
        if ctx.retroalimentacion_del_intento is not None:
            decision = replace(
                decision, estrategia="explicacion_teorica_directa",
                motivo="la propuesta fue refutada: primero comparación y explicación comprobadas",
                modificadores=tuple(m for m in decision.modificadores if m != "autorregulacion"),
                modificadores_suprimidos=decision.modificadores_suprimidos + tuple(
                    m for m in decision.modificadores if m == "autorregulacion"
                ), frase_visible="",
            )
        # `RF-REG-06` · la decisión entera va a la traza y de ahí al registro
        # del turno: se puede reconstruir sin consultar ningún log.
        return replace(ctx, decision_pedagogica=decision), decision.como_dict()
