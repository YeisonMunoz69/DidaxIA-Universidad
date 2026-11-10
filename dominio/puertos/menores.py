from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.evidencia_revisable import (
    EvidenciaRevisable,
    FiltroDeEvidencias,
    PaginaDeEvidencias,
    PosicionDeCursor,
)
from dominio.modelo.menores import (
    EstadoAsentimiento,
    EventoAsentimiento,
    HistorialDeAsentimiento,
    IntentoDeEvidencia,
    ResultadoDeRevision,
    RevisionDeEvidencia,
)


@runtime_checkable
class PuertoAsentimiento(Protocol):

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoAsentimiento,
        comprobante: str,
    ) -> EventoAsentimiento:

        ...

    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        ...

    def historial(self, sujeto_google: str, *, requerido: bool) -> HistorialDeAsentimiento:
        ...

@runtime_checkable
class PuertoEvidenciaDelRepresentante(Protocol):

    def registrar_intento(
        self,
        sujeto_google: str,
        version: str,
        referencia: str,
        sha256: str,
        tamano_bytes: int,
    ) -> IntentoDeEvidencia:

        ...

    def revisar(
        self,
        evidencia: int,
        revisor: str,
        resultado: ResultadoDeRevision,
        motivo: str = "",
    ) -> RevisionDeEvidencia:

        ...

    def intentos(self, sujeto_google: str) -> tuple[IntentoDeEvidencia, ...]:
        ...

    def cola(
        self,
        *,
        actor: str,
        filtro: FiltroDeEvidencias = FiltroDeEvidencias.PENDIENTE,
        limite: int = 20,
        cursor: PosicionDeCursor | None = None,
    ) -> PaginaDeEvidencias:

        ...

    def detalle(self, evidencia: int, *, actor: str) -> EvidenciaRevisable:
        ...

    def referencia_del_documento(self, evidencia: int, *, actor: str) -> str:
        ...
