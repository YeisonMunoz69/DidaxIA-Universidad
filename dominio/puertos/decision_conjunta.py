from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dominio.puertos.almacen import EscrituraRechazada
from dominio.puertos.gobierno import SupresionEnCurso


__all__ = [
    "DecisionYaVigente",
    "PuertoDecisionConjunta",
    "RedecisionNoRequerida",
    "RevocacionRequerida",
    "SupresionEnCurso",
    "VersionesFaltantes",
]

if TYPE_CHECKING:
    from dominio.modelo.consentimiento import Alcance
    from dominio.modelo.decision_conjunta import ActosDeLaDecision, Decision

class VersionesFaltantes(EscrituraRechazada):

    def __init__(self, alcances: tuple[Alcance, ...]) -> None:
        self.alcances = tuple(alcances)
        nombres = ", ".join(f"«{a.value}»" for a in self.alcances)
        super().__init__(f"no hay ninguna versión vigente de: {nombres}")

class RedecisionNoRequerida(EscrituraRechazada):
    pass

class DecisionYaVigente(RedecisionNoRequerida):
    pass

class RevocacionRequerida(RedecisionNoRequerida):
    pass

@runtime_checkable
class PuertoDecisionConjunta(Protocol):

    def registrar_decision(
        self, sujeto_google: str, decision: Decision
    ) -> ActosDeLaDecision:

        ...
