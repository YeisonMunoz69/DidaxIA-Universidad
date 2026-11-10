from __future__ import annotations

import os

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import ErrorDeAlmacen, EscrituraRechazada

VARIABLE_PROPIETARIOS = "INVESTIGADORES_PROPIETARIOS"
VARIABLE_INVESTIGADORES = "INVESTIGADORES_AUTORIZADOS"


def _normalizar(correo: str) -> str:
    return (correo or "").strip().lower()

def propietarios_configurados() -> frozenset[str]:
    return frozenset(
        normalizado
        for fragmento in os.environ.get(VARIABLE_PROPIETARIOS, "").replace(";", ",").split(",")
        if (normalizado := _normalizar(fragmento))
    )

def investigadores_configurados() -> frozenset[str]:
    correos = ",".join(
        (
            os.environ.get(VARIABLE_PROPIETARIOS, ""),
            os.environ.get(VARIABLE_INVESTIGADORES, ""),
        )
    )
    return frozenset(
        normalizado
        for fragmento in correos.replace(";", ",").split(",")
        if (normalizado := _normalizar(fragmento))
    )

def esta_configurado(correo: str) -> bool:
    return _normalizar(correo) in investigadores_configurados()

def es_propietario(correo: str) -> bool:
    return _normalizar(correo) in propietarios_configurados()

def sincronizar_rol_configurado(*, roles, sujeto_google: str, correo: str) -> None:
    if not esta_configurado(correo):
        return
    if puede_revisar_evidencia(roles.roles_de(sujeto_google)):
        return
    try:
        roles.asignar(
            sujeto_google,
            Rol.INVESTIGADOR_ADMINISTRADOR,
            otorgado_por=None,
        )
    except EscrituraRechazada:
        if not puede_revisar_evidencia(roles.roles_de(sujeto_google)):
            raise

def aprovisionar_rol_configurado(*, roles, sujeto_google: str, correo: str) -> bool:
    if roles is None:
        return True
    try:
        sincronizar_rol_configurado(
            roles=roles,
            sujeto_google=sujeto_google,
            correo=correo,
        )
        return True
    except ErrorDeAlmacen:
        return False
