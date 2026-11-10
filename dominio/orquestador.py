from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress

from dominio.filtros.base import Filtro
from dominio.filtros.recuperacion import FiltroRecuperacion
from dominio.modelo.turno import ContextoTurno, TrazaFiltro


class ErrorDeOrquestacion(Exception):

    def __init__(self, causa: Exception, ctx_parcial: ContextoTurno) -> None:
        super().__init__(str(causa))
        self.causa = causa
        self.ctx_parcial = ctx_parcial

class Orquestador:

    def __init__(self, filtros: Sequence[Filtro]) -> None:
        self._calientes = tuple(f for f in filtros if f.ruta == "caliente")
        self._frias = tuple(f for f in filtros if f.ruta == "fría")

    def ejecutar(self, ctx: ContextoTurno, *, al_iniciar=None) -> ContextoTurno:
        return self._ejecutar_lista(self._calientes, ctx, al_iniciar=al_iniciar)

    def ejecutar_fria(self, ctx: ContextoTurno) -> ContextoTurno:
        return self._ejecutar_lista(self._frias, ctx)

    def _ejecutar_lista(
        self, filtros: tuple[Filtro, ...], ctx: ContextoTurno, *, al_iniciar=None
    ) -> ContextoTurno:
        for filtro in filtros:
            if isinstance(filtro, FiltroRecuperacion) and not ctx.procede_recuperar:
                ctx = ctx.con_traza(
                    TrazaFiltro(
                        filtro=filtro.nombre,
                        latencia_ms=0.0,
                        ruta=filtro.ruta,
                        metadatos={
                            "omitido": True,
                            "motivo": "la compuerta de contexto del filtro 4 "
                            "decidió no recuperar para este turno",
                        },
                    )
                )
                continue
            if al_iniciar is not None:
                with suppress(Exception):
                    al_iniciar(filtro.nombre)
            try:
                ctx = filtro.ejecutar(ctx)
            except Exception as exc:
                raise ErrorDeOrquestacion(exc, ctx) from exc
        return ctx
