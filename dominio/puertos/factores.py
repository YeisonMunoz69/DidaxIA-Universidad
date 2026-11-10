from typing import Protocol

from dominio.modelo.turno import ContextoTurno


class PuertoFactores(Protocol):
    def registrar(self, ctx: ContextoTurno) -> bool: ...
