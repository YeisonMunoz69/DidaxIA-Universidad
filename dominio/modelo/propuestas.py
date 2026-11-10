from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PropuestaInvalida(ValueError):
    pass

class EstadoPropuesta(StrEnum):

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"

OPERACIONES_CON_DOBLE_APROBACION: frozenset[str] = frozenset({"retencion.fijar"})


def huella_de(operacion: str, payload: dict) -> str:
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{operacion}␟{canonico}".encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class Propuesta:

    operacion: str
    payload: dict = field(default_factory=dict)
    propuesta_por: str = ""
    propuesta_en: datetime | None = None
    estado: EstadoPropuesta = EstadoPropuesta.PENDIENTE
    aprobada_por: str | None = None
    aprobada_en: datetime | None = None
    secuencia: int = 0

    def __post_init__(self) -> None:
        operacion = (self.operacion or "").strip()
        if operacion not in OPERACIONES_CON_DOBLE_APROBACION:
            raise PropuestaInvalida(
                f"{operacion!r} no es una operación que exija doble aprobación (EQ-023)"
            )
        object.__setattr__(self, "operacion", operacion)
        if not isinstance(self.payload, dict):
            raise PropuestaInvalida("el contenido propuesto tiene que ser un objeto")
        object.__setattr__(self, "estado", EstadoPropuesta(self.estado))
        if self.aprobada_por is not None and self.aprobada_por == self.propuesta_por:
            raise PropuestaInvalida("nadie puede aprobar su propia propuesta")

    @property
    def huella(self) -> str:
        return huella_de(self.operacion, self.payload)

    @property
    def pendiente(self) -> bool:
        return self.estado is EstadoPropuesta.PENDIENTE

    def exigir_aprobable_por(self, aprobador: str) -> None:
        if not (aprobador or "").strip():
            raise PropuestaInvalida("una aprobación necesita quién la hace")
        if aprobador == self.propuesta_por:
            raise PropuestaInvalida("nadie puede aprobar su propia propuesta")
        if not self.pendiente:
            raise PropuestaInvalida(
                f"esta propuesta ya está {self.estado.value}: no se aprueba dos veces"
            )
