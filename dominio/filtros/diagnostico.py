from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol, runtime_checkable

from dominio.diagnostico.clasificador import (
    Diagnostico,
    RespuestaDosNiveles,
    clasificar,
)
from dominio.filtros.base import Filtro
from dominio.modelo.matematica import BloqueVerificable, InformeVerificacion, Veredicto
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.sondeo import Desenlace, DesenlaceDelSondeo, validar_respuesta
from dominio.puertos.plantillas import ItemDosNiveles, PuertoPlantillas


@runtime_checkable
class _PuertoDeCorreccion(Protocol):

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion: ...

class FiltroDiagnostico(Filtro):

    nombre = "diagnóstico conceptual de dos niveles"
    ruta = "caliente"

    def __init__(
        self,
        plantillas: PuertoPlantillas | None = None,
        simbolico: _PuertoDeCorreccion | None = None,
    ) -> None:
        self._plantillas = plantillas
        self._simbolico = simbolico

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        diagnostico, desenlace = self._diagnosticar(ctx)
        if diagnostico is None:
            return replace(ctx, desenlace_del_sondeo=desenlace), {
                "diagnosticado": False,
                "motivo": desenlace.motivo,

                "desenlace": desenlace.estado.value,
            }

        meta = {
            "diagnosticado": True,
            "estado": diagnostico.estado,
            "nombre": diagnostico.nombre,
            "nodo": diagnostico.nodo,
            "siguiente": diagnostico.siguiente,
            "concepcion": diagnostico.concepcion or "",

            "motivo": diagnostico.motivo,
            "desenlace": desenlace.estado.value,
        }
        return replace(
            ctx, diagnostico=diagnostico, desenlace_del_sondeo=desenlace
        ), meta

    def _diagnosticar(
        self, ctx: ContextoTurno
    ) -> tuple[Diagnostico | None, DesenlaceDelSondeo]:

        cruda = ctx.respuesta_al_item
        if cruda is None:
            return None, DesenlaceDelSondeo(
                estado=Desenlace.SIN_RESPUESTA,
                motivo="el turno no responde a un ítem de dos niveles",
            )
        if self._plantillas is None:

            return None, DesenlaceDelSondeo(
                estado=Desenlace.NO_CLASIFICABLE,
                nodo=cruda.nodo,
                motivo="sin puerto de plantillas: no hay banco de ítems que consultar",
            )

        item = self._plantillas.item_de(cruda.nodo)

        veredicto = validar_respuesta(
            cruda, item, ctx.sondeos_ofrecidos, ctx.sondeos_contestados
        )
        if not veredicto.admitida:
            return None, DesenlaceDelSondeo(
                estado=Desenlace.RECHAZADA, nodo=cruda.nodo, motivo=veredicto.motivo
            )

        opcion = item.opcion(cruda.razon)
        correcta = self._turno_1_correcto(item, cruda.resultado)
        if correcta is None:

            return None, DesenlaceDelSondeo(
                estado=Desenlace.NO_CLASIFICABLE,
                nodo=item.nodo,
                motivo="no se pudo comprobar el resultado del turno 1",
            )

        return clasificar(
            RespuestaDosNiveles(
                nodo=item.nodo, respuesta_correcta=correcta, opcion=opcion
            )
        ), DesenlaceDelSondeo(
            estado=Desenlace.PROCESADA,
            nodo=item.nodo,
            motivo="la respuesta se admitió y se clasificó",
        )

    def _turno_1_correcto(self, item: ItemDosNiveles, resultado: str) -> bool | None:
        if self._simbolico is None or not resultado.strip():
            return None
        try:
            informe = self._simbolico.verificar(
                [
                    BloqueVerificable(
                        identificador="turno-1",
                        izquierda=f"d/dx ({item.derivar})",
                        derecha=resultado.strip(),
                        relacion="=",
                    )
                ]
            )
        except Exception:
            return None

        if not informe.verificaciones:
            return None
        veredicto = informe.verificaciones[0].veredicto
        if veredicto is Veredicto.NO_VERIFICABLE:
            return None
        return veredicto is Veredicto.VALIDA
