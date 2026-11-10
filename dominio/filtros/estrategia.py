from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales
from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import Intencion
from dominio.pedagogia.politica import Situacion, decidir


class FiltroEstrategia(Filtro):

    nombre = "selección de estrategia"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        situacion = Situacion(

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

        return replace(ctx, decision_pedagogica=decision), decision.como_dict()
