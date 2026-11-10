from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dominio.modelo.consentimiento import EstadoConsentimiento, transicion_admitida
from dominio.modelo.decision_conjunta import Decision
from dominio.puertos.almacen import TransicionInvalida
from dominio.puertos.decision_conjunta import DecisionYaVigente, RevocacionRequerida

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dominio.modelo.consentimiento import Alcance
    from dominio.modelo.identidad import CategoriaDeEdad

@dataclass(frozen=True, slots=True)
class DimensionDecidible:

    alcance: Alcance
    estado: str
    version: str | None
    version_requerida: str | None
    categoria_del_acto: CategoriaDeEdad | None = None
    categoria_actual: CategoriaDeEdad | None = None

    def refleja(self, decision: Decision) -> bool:
        if self.estado != decision.value:
            return False
        if self.version_requerida is None or self.version != self.version_requerida:
            return False
        return (
            self.categoria_del_acto is None
            or self.categoria_del_acto is self.categoria_actual
        )

@dataclass(frozen=True, slots=True)
class AccionesDeDecision:

    puede_aceptar: bool
    puede_rechazar: bool

    @property
    def requerida(self) -> bool:
        return self.puede_aceptar or self.puede_rechazar

def decision_conjunta_vigente(
    dimensiones: Iterable[DimensionDecidible],
) -> Decision | None:

    candidatas = tuple(dimensiones)
    if not candidatas:
        return None
    for decision in Decision:
        if all(dimension.refleja(decision) for dimension in candidatas):
            return decision
    return None

def _admite_individual(dimension: DimensionDecidible, decision: Decision) -> bool:
    try:
        actual = EstadoConsentimiento(dimension.estado)
    except ValueError:
        return False
    return transicion_admitida(
        actual,
        EstadoConsentimiento(decision.value),
        cambia_version=dimension.version != dimension.version_requerida,
        cambia_categoria=(
            dimension.categoria_del_acto is not None
            and dimension.categoria_del_acto is not dimension.categoria_actual
        ),
    )

def _admite_conjunta(
    dimensiones: tuple[DimensionDecidible, ...], decision: Decision
) -> bool:

    vigente = decision_conjunta_vigente(dimensiones)
    if vigente is None:

        return True
    if vigente is decision:

        return False

    return vigente is Decision.RECHAZADO

def admite_decision(
    dimensiones: Iterable[DimensionDecidible], decision: Decision
) -> bool:

    candidatas = tuple(dimensiones)
    if not candidatas:
        return False
    if len(candidatas) == 1:
        return _admite_individual(candidatas[0], decision)
    return _admite_conjunta(candidatas, decision)

def acciones_disponibles(
    dimensiones: Iterable[DimensionDecidible],
) -> AccionesDeDecision:

    candidatas = tuple(dimensiones)
    return AccionesDeDecision(
        puede_aceptar=admite_decision(candidatas, Decision.OTORGADO),
        puede_rechazar=admite_decision(candidatas, Decision.RECHAZADO),
    )

def exigir_redecision(
    dimensiones: Iterable[DimensionDecidible], decision: Decision
) -> None:

    candidatas = tuple(dimensiones)
    if not candidatas:
        raise DecisionYaVigente(
            "no hay ninguna dimensión sobre la que decidir en esta decisión conjunta"
        )
    if admite_decision(candidatas, decision):
        return

    vigente = decision_conjunta_vigente(candidatas)
    if vigente is decision:
        raise DecisionYaVigente(
            f"esta decisión ya está registrada como {decision.value!r} sobre las "
            "versiones que rigen ahora: no hay nada nuevo que decidir"
        )
    if vigente is Decision.OTORGADO:
        raise RevocacionRequerida(
            "hay una autorización vigente y al día; para retirarla se revoca, no se "
            "rechaza: son dos actos con semántica distinta"
        )

    raise TransicionInvalida(
        f"no se puede pasar a {decision.value!r} desde el estado actual sin una "
        "decisión nueva que registrar"
    )
