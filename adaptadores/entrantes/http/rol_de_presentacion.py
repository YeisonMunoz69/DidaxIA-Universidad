from __future__ import annotations

from typing import TYPE_CHECKING

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import AlmacenNoConfigurado

if TYPE_CHECKING:
    from adaptadores.entrantes.http.docentes import RegistroDeDocentes
    from dominio.puertos.roles import PuertoAsignacionDeRoles

ROL_ESTUDIANTE = "estudiante"
ROL_DOCENTE = "docente"
ROL_INVESTIGADOR = "investigador"


PRIORIDAD = (ROL_INVESTIGADOR, ROL_DOCENTE, ROL_ESTUDIANTE)


def rol_de_presentacion(
    *,
    roles: PuertoAsignacionDeRoles | None,
    registro_docentes: RegistroDeDocentes,
    sujeto_google: str,
    correo: str,
) -> str:

    if roles is None:

        raise AlmacenNoConfigurado(
            "no hay registro de roles cableado: no se puede determinar el rol "
            "de esta cuenta"
        )
    roles_vigentes = roles.roles_de(sujeto_google)
    if puede_revisar_evidencia(roles_vigentes):
        return ROL_INVESTIGADOR
    if Rol.DOCENTE in roles_vigentes:
        return ROL_DOCENTE
    if registro_docentes.es_docente(correo):
        return ROL_DOCENTE
    return ROL_ESTUDIANTE
