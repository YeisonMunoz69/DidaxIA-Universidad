from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dominio.modelo.telemetria import EventoTelemetria

@runtime_checkable
class PuertoTelemetria(Protocol):
    def registrar(
        self, evento: EventoTelemetria, *, alcance_institucional: bool = False
    ) -> bool:

        ...
