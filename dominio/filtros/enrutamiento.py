from __future__ import annotations

from dataclasses import replace
from typing import Protocol, runtime_checkable

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import EMOCIONAL, familia_de
from dominio.puertos.plantillas import PuertoPlantillas


@runtime_checkable
class IdentificadorDeNodo(Protocol):

    def identificar_nodo(self, consulta: str) -> str | None:
        ...

class FiltroEnrutamiento(Filtro):

    nombre = "enrutamiento y compuerta de contexto"
    ruta = "caliente"

    def __init__(
        self,
        identificador: IdentificadorDeNodo,
        plantillas: PuertoPlantillas | None = None,
    ) -> None:
        self._identificador = identificador
        self._plantillas = plantillas

    def _ejercicio_declarado(self, ctx: ContextoTurno) -> str | None:
        if self._plantillas is None:
            return None
        for expresion in self._candidatas(ctx):
            nodo = self._plantillas.nodo_del_ejercicio(expresion)
            if nodo:
                return nodo
        return None

    @staticmethod
    def _candidatas(ctx: ContextoTurno) -> tuple[str, ...]:
        del_turno = tuple(ctx.expresiones)
        estado = ctx.estado_conversacion
        activo = estado.problema.unidad.expresion if estado is not None else ""
        return (*del_turno, activo) if activo else del_turno

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        lexico = self._identificador.identificar_nodo(ctx.texto_estudiante)
        declarado = self._ejercicio_declarado(ctx)
        nodo = declarado or lexico

        familia = familia_de(ctx.intencion)
        procede = not (familia == EMOCIONAL and not ctx.expresiones)

        meta = {
            "nodo_activo": nodo or "",
            "nodo_identificado": nodo is not None,

            "nodo_por_ejercicio_declarado": declarado or "",
            "nodo_por_coincidencia_lexica": lexico or "",
            "procede_recuperar": procede,
            "intencion_considerada": ctx.intencion,
            "familia_considerada": familia,
        }
        nuevo = replace(ctx, nodo_activo=nodo or "", procede_recuperar=procede)
        return nuevo, meta
