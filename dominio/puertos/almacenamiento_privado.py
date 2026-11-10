from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.puertos.almacen import ErrorDeAlmacen


class AlmacenamientoNoConfigurado(ErrorDeAlmacen):
    pass

class AlmacenamientoNoDisponible(ErrorDeAlmacen):
    pass

class DocumentoAusente(AlmacenamientoNoDisponible):
    pass

class DocumentoPendienteDeConfirmacion(AlmacenamientoNoDisponible):
    pass

@runtime_checkable
class PuertoAlmacenamientoPrivado(Protocol):

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        ...

    def confirmar(self, referencia: str) -> None:
        ...

    def retirar(self, referencia: str) -> bool:
        ...

    def recuperar(self, referencia: str) -> bytes:
        ...

    def pendientes(self) -> tuple[str, ...]:
        ...

    def esta_configurado(self) -> bool:
        ...
