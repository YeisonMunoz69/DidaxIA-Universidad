from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.acceso import EstadoVigente


@runtime_checkable
class PuertoEstadoVigente(Protocol):

    def estado_vigente(self, sujeto_google: str) -> EstadoVigente | None:
        ...
