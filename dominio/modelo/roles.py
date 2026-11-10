from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RolInvalido(ValueError):
    pass

class Rol(StrEnum):

    INVESTIGADOR_ADMINISTRADOR = "investigador_administrador"
    DOCENTE = "docente"

def _sujeto(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise RolInvalido(f"{campo} tiene que ser un sujeto estable")
    return valor.strip()

def _sujeto_opcional(valor: str | None, campo: str) -> str | None:
    return None if valor is None else _sujeto(valor, campo)

@dataclass(frozen=True, slots=True)
class AsignacionDeRol:

    sujeto_google: str
    rol: Rol
    otorgado_en: datetime
    otorgado_por: str | None = None

    revocado_por: str | None = None
    revocado_en: datetime | None = None
    secuencia: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "sujeto_google", _sujeto(self.sujeto_google, "sujeto_google"))
        object.__setattr__(self, "rol", Rol(self.rol))
        if not isinstance(self.otorgado_en, datetime):
            raise RolInvalido("una asignación conserva cuándo se otorgó")
        object.__setattr__(self, "otorgado_por", _sujeto_opcional(self.otorgado_por, "otorgado_por"))
        object.__setattr__(self, "revocado_por", _sujeto_opcional(self.revocado_por, "revocado_por"))
        self._exigir_revocacion_auditada()

    def _exigir_revocacion_auditada(self) -> None:
        if (self.revocado_en is None) != (self.revocado_por is None):
            raise RolInvalido(
                "una revocación registra quién la realizó y cuándo, o no se registra"
            )
        if self.revocado_en is None:
            return
        if not isinstance(self.revocado_en, datetime):
            raise RolInvalido("revocado_en tiene que ser una fecha")
        if self.revocado_en < self.otorgado_en:
            raise RolInvalido("una revocación no puede ser anterior al otorgamiento")

    @property
    def vigente(self) -> bool:
        return self.revocado_en is None

def puede_revisar_evidencia(roles: Iterable[Rol]) -> bool:
    return Rol.INVESTIGADOR_ADMINISTRADOR in set(roles)
