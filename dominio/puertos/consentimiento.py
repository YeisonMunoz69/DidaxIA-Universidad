from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PuertoConsentimiento(Protocol):

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:

        ...

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        ...
