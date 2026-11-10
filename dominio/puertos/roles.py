from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.roles import AsignacionDeRol, Rol


@runtime_checkable
class PuertoAsignacionDeRoles(Protocol):

    def asignar(
        self, sujeto_google: str, rol: Rol, otorgado_por: str | None = None
    ) -> AsignacionDeRol:

        ...

    def revocar(self, sujeto_google: str, rol: Rol, revocado_por: str) -> bool:
        ...

    def roles_de(self, sujeto_google: str) -> frozenset[Rol]:
        ...

    def asignaciones(self, sujeto_google: str) -> tuple[AsignacionDeRol, ...]:
        ...

    def directorio_institucional(
        self, investigador: str, filtro: str = "", pertenencia: str = "todas",
        clase: str = "",
    ) -> list[dict]:

        ...

    def asignar_facultad_profesional(
        self, investigador: str, sujeto: str, facultad: str
    ) -> dict | None:

        ...
