"""
roles.py — Funciones profesionales persistentes y auditadas (`EQ-023`)
========================================================================

⚠️ **Esto no es un segundo sistema de roles, y conviene leer por qué antes de
tocarlo.**

Compatibilidad con lo que ya existe
--------------------------------------
El sistema ya resolvía `estudiante` y `docente` en
`adaptadores/entrantes/http/docentes.py`, con una lista manual y la cola
persistida en `solicitud_docente`. Esa compatibilidad se conserva. Desde la
migración 22, las altas nuevas de docente y de investigador comparten este
registro persistente y auditable.

Lo que gobierna este módulo
--------------------------------------------------------
`Rol` contiene las dos funciones profesionales administrables:
`investigador_administrador` y `docente`. `estudiante` no es una asignación:
es la experiencia base de toda cuenta institucional. El CHECK final de
`rol_asignacion`, ampliado por la migración 22, admite el mismo catálogo.

Un rol es una asignación, no un correo escrito en el código
-------------------------------------------------------------------
El encargo lo pide con todas las letras: *«el rol no debe derivarse de un correo
hardcodeado dentro del dominio»*. Aquí no hay ninguna dirección; hay
`AsignacionDeRol`, que cuelga del sujeto estable, dice quién la otorgó y cuándo,
y se retira poniéndole fecha de revocación en vez de borrando la fila. Las
cuentas propietarias se aprovisionan desde el entorno y las delegadas mediante
una operación explícita y auditable.

Retirar también se audita
--------------------------------
La primera entrega guardaba `revocado_en` y no guardaba quién. La revisión lo
devolvió, y con razón: una aprobación de hace un mes se explica por el permiso
que existía entonces, y si el permiso desaparece sin autor no queda a quién
preguntarle por qué. Desde la corrección, `revocado_por` y `revocado_en` van
juntos o la fila no se acepta.


"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RolInvalido(ValueError):
    """Una asignación que no se puede aceptar."""


class Rol(StrEnum):
    """Roles profesionales persistentes que gobierna el equipo investigador."""

    INVESTIGADOR_ADMINISTRADOR = "investigador_administrador"
    DOCENTE = "docente"


def _sujeto(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise RolInvalido(f"{campo} tiene que ser un sujeto estable")
    return valor.strip()


def _sujeto_opcional(valor: str | None, campo: str) -> str | None:
    """Un sujeto estable, o `None`. Sin valores intermedios: una cadena en blanco
    sería «alguien sin nombre», que es justo lo que una auditoría no admite."""
    return None if valor is None else _sujeto(valor, campo)


@dataclass(frozen=True, slots=True)
class AsignacionDeRol:
    """Quién tiene qué rol, desde cuándo, por decisión de quién.

    `otorgado_por` admite `None` para la primera asignación del sistema: no hay
    todavía nadie con el rol que pueda concederlo, y fingir un otorgante sería
    inventar una autoría. Quién ejecuta esa primera asignación y con qué
    procedimiento es una decisión operativa del equipo, no de este tipo.
    """

    sujeto_google: str
    rol: Rol
    otorgado_en: datetime
    otorgado_por: str | None = None
    #: Quién retiró el rol y cuándo. Van **juntos o no van**: una revocación sin
    #: autor no explica quién dejó de confiar, y `EQ-023` audita cada cambio de
    #: permisos igual que cada consulta de una conversación. La misma pareja la
    #: exige un CHECK en `rol_asignacion`.
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
        """Fecha y autor de la revocación van juntos, o no van.

        Separado de `__post_init__` porque es una regla con nombre propio —la que
        la revisión echó en falta— y porque leerla junto a las validaciones de
        forma la escondía.
        """
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
    """`EQ-023`: un investigador autorizado verifica la autorización.

    Se pregunta por el rol y nunca por el correo. Es la única capacidad que esta
    sesión ata al rol; el resto de la matriz de permisos de `EQ-023` sigue siendo
    una decisión abierta del equipo y no se anticipa aquí.
    """
    return Rol.INVESTIGADOR_ADMINISTRADOR in set(roles)
