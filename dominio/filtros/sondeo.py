from __future__ import annotations

from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import EMOCIONAL, familia_de
from dominio.pedagogia.sondeo import decidir
from dominio.pedagogia.configuracion_sondeos import NODOS_DIGITALES
from dominio.puertos.plantillas import PuertoPlantillas


class FiltroSondeo(Filtro):

    nombre = "ofrecimiento del ítem de dos niveles"
    ruta = "caliente"

    def __init__(self, plantillas: PuertoPlantillas | None = None, configuracion=None) -> None:
        self._plantillas = plantillas
        self._configuracion = configuracion

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if self._plantillas is None or not ctx.nodo_activo:
            return ctx, {
                "procede": False,
                "motivo": (
                    "sin banco de ítems" if self._plantillas is None
                    else "el turno no tiene nodo activo"
                ),
            }

        habilitado, umbral = True, 2
        if self._configuracion is not None and ctx.nodo_activo in NODOS_DIGITALES:
            try:
                vigente = self._configuracion.consultar()
            except Exception:
                return ctx, {"procede": False, "motivo": "configuración curricular no disponible"}
            habilitado = vigente.habilitado(ctx.nodo_activo)
            umbral = vigente.umbral_intentos

        ofrecimiento = decidir(
            _item_de(self._plantillas, ctx.nodo_activo),

            intencion=familia_de(ctx.intencion) if ctx.intencion else "",
            trae_expresion=bool(ctx.expresiones),
            intentos_en_el_problema=ctx.señales.intentos_en_el_problema if ctx.señales else 0,
            estado=ctx.estado_de_sondeo,
            habilitado=habilitado,
            umbral_intentos=umbral,
        )
        meta = {"procede": ofrecimiento.procede, "motivo": ofrecimiento.motivo}
        if not ofrecimiento.procede:
            return ctx, meta
        meta["nodo"] = ofrecimiento.item.nodo
        return replace(ctx, item_ofrecido=ofrecimiento.item), meta

def _item_de(plantillas: PuertoPlantillas, nodo: str):
    try:
        return plantillas.item_de(nodo)
    except Exception:
        return None

__all__ = ["EMOCIONAL", "FiltroSondeo"]
