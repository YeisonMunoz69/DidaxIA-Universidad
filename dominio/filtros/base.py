from __future__ import annotations

import time
from abc import ABC, abstractmethod

from dominio.modelo.turno import ContextoTurno, TrazaFiltro


class Filtro(ABC):

    nombre: str = ""

    ruta: str = "caliente"

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if not getattr(cls, "nombre", ""):
            raise TypeError(f"{cls.__name__} debe declarar su nombre en la cadena")
        if cls.ruta not in ("caliente", "fría"):
            raise TypeError(f"{cls.__name__}: la ruta debe ser «caliente» o «fría»")

    @abstractmethod
    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        pass

    def ejecutar(self, ctx: ContextoTurno) -> ContextoTurno:
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
