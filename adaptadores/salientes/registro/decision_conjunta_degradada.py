from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from dominio.puertos.almacen import AlmacenNoConfigurado

if TYPE_CHECKING:
    from dominio.modelo.decision_conjunta import Decision

class AdaptadorDecisionConjuntaDegradado:

    def registrar_decision(self, sujeto_google: str, decision: Decision) -> NoReturn:
        raise AlmacenNoConfigurado(
            "no hay base en la que registrar una decisión de consentimiento: la "
            "composición no cableó ninguna"
        )
