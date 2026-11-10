from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from dominio.modelo.roles import Rol


class EstadoDeInvitacion(StrEnum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    REVOCADA = "revocada"
    EXPIRADA = "expirada"

@dataclass(frozen=True, slots=True)
class InvitacionDeRol:
    secuencia: int
    correo: str
    rol: Rol
    emitida_por: str
    emitida_en: datetime
    expira_en: datetime
    estado: EstadoDeInvitacion
    aceptada_en: datetime | None = None
    revocada_en: datetime | None = None

    def como_publica(self) -> dict:
        return {
            "id": self.secuencia,
            "correo": self.correo,
            "rol": self.rol.value,
            "emitida_por": self.emitida_por,
            "emitida_en": self.emitida_en.isoformat(),
            "expira_en": self.expira_en.isoformat(),
            "estado": self.estado.value,
            "aceptada_en": self.aceptada_en.isoformat() if self.aceptada_en else None,
            "revocada_en": self.revocada_en.isoformat() if self.revocada_en else None,
        }
