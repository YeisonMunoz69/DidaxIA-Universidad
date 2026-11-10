from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from dominio.modelo.matematica import (
    BloqueVerificable,
    InformeVerificacion,
    Precomputo,
)


@runtime_checkable
class PuertoSimbolico(Protocol):

    def precomputar(
        self,
        expresion: str,
        variable: str = "x",
        orden: int = 1,
        notacion: str = "",
    ) -> Precomputo:

        ...

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion:
        ...
