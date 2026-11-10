from __future__ import annotations

from typing import Any

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import EscrituraRechazada


_SQL_ROLES_VIGENTES = """
SELECT rol FROM rol_asignacion
 WHERE sujeto_google = %s AND revocado_en IS NULL
 FOR SHARE
"""


MOTIVO_SIN_ROL = "esta operación la reserva EQ-023 a un investigador administrador vigente"


DOCENTE_VIGENTE_SQL = (
    "EXISTS (SELECT 1 FROM rol_asignacion ra WHERE ra.sujeto_google=p.sujeto_google "
    "AND ra.rol='docente' AND ra.revocado_en IS NULL)"
)


MOTIVO_SOBRE_SI_MISMO = "nadie puede otorgarse ni retirarse un rol a sí mismo (EQ-023)"


def roles_vigentes_bloqueados(cur: Any, sujeto: str) -> frozenset[Rol]:
    cur.execute(_SQL_ROLES_VIGENTES, (sujeto,))
    return frozenset(Rol(fila[0]) for fila in cur.fetchall())

def exigir_investigador_administrador(cur: Any, actor: str) -> None:
    if not puede_revisar_evidencia(roles_vigentes_bloqueados(cur, actor)):
        raise EscrituraRechazada(MOTIVO_SIN_ROL)

def exigir_actor_distinto(actor: str, sujeto: str) -> None:
    if actor == sujeto:
        raise EscrituraRechazada(MOTIVO_SOBRE_SI_MISMO)
