from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales, decidir
from dominio.arbitraje.intervencion import decidir_intervencion
from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno


class FiltroArbitraje(Filtro):

    nombre = "arbitraje de intervención"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        aportadas = ctx.señales is not None
        señales = ctx.señales or Señales()

        divulgacion = decidir(señales, peticion=ctx.intencion_detalle)
        intervencion = decidir_intervencion(señales)

        meta = {
            "divulgacion": {
                "nivel": divulgacion.nivel,
                "nombre": divulgacion.nombre,
                "motivo": divulgacion.motivo,
                "alcance": divulgacion.alcance,

                "descartadas": divulgacion.descartadas,
                "sin_evaluar": divulgacion.sin_evaluar,
                "no_escalan": divulgacion.no_escalan,
            },
            "intervencion": {
                "nivel": intervencion.nivel,
                "nombre": intervencion.nombre,
                "motivo": intervencion.motivo,
                "descartadas": intervencion.descartadas,
                "sin_evaluar": intervencion.sin_evaluar,
            },
            "señales_aportadas": aportadas,
        }
        return (
            replace(
                ctx,
                nivel_divulgacion=divulgacion.nivel,
                alcance_divulgacion=divulgacion.alcance,
                nivel_intervencion=intervencion.nivel,
            ),
            meta,
        )
