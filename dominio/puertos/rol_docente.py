from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADA = "aprobada"
ESTADO_RECHAZADA = "rechazada"


@dataclass
class Solicitud:

    identificador: str
    correo: str
    creada: str
    estado: str = ESTADO_PENDIENTE

    nota: str | None = None

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "correo": self.correo,
            "creada": self.creada,
            "estado": self.estado,
            "nota": self.nota,
        }

@runtime_checkable
class PuertoSolicitudesDocentes(Protocol):

    def solicitar(self, correo: str) -> Solicitud:
        ...

    def listar_pendientes(self) -> list[Solicitud]:
        ...

    def aprobar(self, identificador: str) -> bool:
        ...

    def rechazar(self, identificador: str, motivo: str) -> bool:
        ...

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        ...

    def aprobada(self, correo: str) -> bool:
        ...
