from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dominio.kpi.consulta import ConsultaKPI

@runtime_checkable
class PuertoCalculoKPI(Protocol):
    def calcular(self, consulta: ConsultaKPI) -> dict:
        ...
