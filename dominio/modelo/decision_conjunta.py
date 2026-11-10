from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.menores import EstadoAsentimiento


class DecisionInvalida(ValueError):
    pass

class Decision(StrEnum):

    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"

    @property
    def como_consentimiento(self) -> EstadoConsentimiento:
        return EstadoConsentimiento(self.value)

    @property
    def como_asentimiento(self) -> EstadoAsentimiento:
        return EstadoAsentimiento(self.value)

def decision_desde(valor: object) -> Decision | None:
    if not isinstance(valor, str):
        return None
    try:
        return Decision(valor)
    except ValueError:
        return None

ORDEN_DE_LOS_ACTOS: tuple[Alcance, ...] = (Alcance.TITULAR, Alcance.ASENTIMIENTO)


@dataclass(frozen=True, slots=True)
class ActoRegistrado:

    alcance: Alcance
    version: str
    decision: Decision
    comprobante: str
    momento: datetime
    secuencia: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        object.__setattr__(self, "decision", Decision(self.decision))
        if not isinstance(self.version, str) or not self.version.strip():
            raise DecisionInvalida("un acto registrado tiene que nombrar su versión")
        if not isinstance(self.comprobante, str) or not SHA256.fullmatch(self.comprobante):
            raise DecisionInvalida("el comprobante tiene que ser un SHA-256 en minúsculas")
        if not isinstance(self.momento, datetime):
            raise DecisionInvalida("momento tiene que ser la fecha que asignó el almacén")
        if isinstance(self.secuencia, bool) or not isinstance(self.secuencia, int):
            raise DecisionInvalida("la secuencia es el identificador que asignó el almacén")
        if self.secuencia <= 0:
            raise DecisionInvalida("un acto sin secuencia no está persistido")

@dataclass(frozen=True, slots=True)
class ActosDeLaDecision:

    sujeto_google: str
    actos: tuple[ActoRegistrado, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.sujeto_google, str) or not self.sujeto_google.strip():
            raise DecisionInvalida("los actos pertenecen a un sujeto y hay que decir cuál")
        actos = tuple(self.actos)
        if not actos:
            raise DecisionInvalida("una decisión registrada tiene al menos un acto")
        alcances = tuple(a.alcance for a in actos)
        if alcances != ORDEN_DE_LOS_ACTOS[: len(alcances)]:
            raise DecisionInvalida(
                "los actos de una decisión van en el orden "
                f"{[a.value for a in ORDEN_DE_LOS_ACTOS]} y llegaron "
                f"{[a.value for a in alcances]}"
            )
        if len({a.decision for a in actos}) != 1:
            raise DecisionInvalida(
                "una sola acción visible no puede otorgar en una dimensión y "
                "rechazar en la otra"
            )
        object.__setattr__(self, "actos", actos)

    @property
    def decision(self) -> Decision:
        return self.actos[0].decision

    @property
    def titular(self) -> ActoRegistrado:
        return self.actos[0]

    @property
    def incluye_asentimiento(self) -> bool:
        return len(self.actos) > 1
