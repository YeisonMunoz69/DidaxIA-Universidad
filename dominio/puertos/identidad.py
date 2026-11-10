from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.identidad import Identidad, PerfilOnboarding


@runtime_checkable
class PuertoIdentidad(Protocol):

    def registrar(self, identidad: Identidad) -> PerfilOnboarding:
        ...

    def declarar_perfil(
        self,
        sujeto_google: str,
        *,
        edad: int | None = None,
        facultad: str = "",
        programa: str = "",
        semestre: int | None = None,
        motivo: str = "",
        origen: str = "onboarding_estudiante",
    ) -> PerfilOnboarding:

        ...

    def consultar(self, sujeto_google: str) -> PerfilOnboarding | None:
        ...

    def fijar_limite_representante(self, sujeto_google: str, limite: datetime) -> None:
        ...
