from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.consentimiento import (
    Alcance,
    EstadoConsentimiento,
    EventoConsentimiento,
    HistorialDeConsentimiento,
    VersionDeConsentimiento,
)


@runtime_checkable
class PuertoVersionesDeConsentimiento(Protocol):

    def registrar_version(self, version: VersionDeConsentimiento) -> None:
        ...

    def consultar_version(self, codigo: str) -> VersionDeConsentimiento | None:
        ...

    def versiones(self, alcance: Alcance | None = None) -> tuple[VersionDeConsentimiento, ...]:
        ...

    def version_requerida(self, alcance: Alcance) -> VersionDeConsentimiento | None:
        ...

@runtime_checkable
class PuertoEventosDeConsentimiento(Protocol):

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoConsentimiento,
        comprobante: str,
    ) -> EventoConsentimiento:

        ...

    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        ...

    def historial(self, sujeto_google: str) -> HistorialDeConsentimiento:
        ...
