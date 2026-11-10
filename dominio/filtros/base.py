"""
base.py — Contrato común de los filtros
=======================================

`ADR-001` §6.3: cada filtro recibe y devuelve el mismo objeto de contexto y
emite una traza con su latencia. Aquí ese contrato se hace **imposible de
incumplir por descuido**: `Filtro.ejecutar` mide y añade la traza, y las
subclases implementan `_procesar`, que no puede devolver un contexto sin ella.

Es la diferencia entre una propiedad que la arquitectura sostiene y una que
depende de que nadie se olvide.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from dominio.modelo.turno import ContextoTurno, TrazaFiltro


class Filtro(ABC):
    """Etapa de la cadena de procesamiento del turno."""

    #: Nombre que aparece en la traza. Debe ser el del catálogo, no uno cómodo.
    nombre: str = ""

    #: «caliente» o «fría», según la asignación de `ADR-001` §6.3.
    ruta: str = "caliente"

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if not getattr(cls, "nombre", ""):
            raise TypeError(f"{cls.__name__} debe declarar su nombre en la cadena")
        if cls.ruta not in ("caliente", "fría"):
            raise TypeError(f"{cls.__name__}: la ruta debe ser «caliente» o «fría»")

    @abstractmethod
    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        """Trabajo del filtro. Devuelve el contexto nuevo y sus metadatos."""

    def ejecutar(self, ctx: ContextoTurno) -> ContextoTurno:
        """Ejecuta el filtro midiendo su latencia y dejando su traza."""
        inicio = time.perf_counter()
        nuevo, meta = self._procesar(ctx)
        latencia = (time.perf_counter() - inicio) * 1000
        return nuevo.con_traza(
            TrazaFiltro(
                filtro=self.nombre,
                latencia_ms=latencia,
                ruta=self.ruta,
                metadatos=meta,
            )
        )
