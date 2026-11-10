from __future__ import annotations

from datetime import timedelta
from typing import Protocol, runtime_checkable

from dominio.modelo.invitaciones import InvitacionDeRol
from dominio.modelo.roles import Rol


@runtime_checkable
class PuertoInvitaciones(Protocol):
    def emitir(
        self, correo: str, rol: Rol, *, emisor: str, token_huella: str,
        vigencia: timedelta,
    ) -> InvitacionDeRol: ...

    def listar(self, actor: str) -> tuple[InvitacionDeRol, ...]: ...

    def revocar(self, secuencia: int, *, actor: str) -> InvitacionDeRol | None: ...

    def aceptar_del_primer_inicio(
        self, correo: str, sujeto: str, token_huella: str
    ) -> tuple[Rol, ...]: ...
