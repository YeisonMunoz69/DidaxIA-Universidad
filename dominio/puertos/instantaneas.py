from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)


@dataclass(frozen=True, slots=True)
class ResultadoDePublicacion:

    codigo: str
    escrita: bool
    motivo: str = ""

@runtime_checkable
class PuertoInstantaneasDeConsentimiento(Protocol):

    def publicar(self, publicacion: PublicacionDeVersion) -> ResultadoDePublicacion:
        ...

    def publicar_lote(
        self, publicaciones: Sequence[PublicacionDeVersion]
    ) -> tuple[ResultadoDePublicacion, ...]:

        ...

    def instantanea_de(self, codigo: str) -> InstantaneaDeVersion | None:
        ...
