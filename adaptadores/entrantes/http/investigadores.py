"""Aprovisionamiento explícito de investigadores desde el entorno.

``INVESTIGADORES_AUTORIZADOS`` es la lista operativa de arranque, equivalente
a ``DOCENTES_AUTORIZADOS`` pero con una diferencia importante: el permiso de
investigación se materializa en ``rol_asignacion``. Al iniciar sesión, una
cuenta configurada que todavía no tenga el rol recibe la asignación de
bootstrap; desde ese momento todas las rutas conservan su comprobación
transaccional habitual y no dependen de comparaciones de correo dispersas.
"""

from __future__ import annotations

import os

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import ErrorDeAlmacen, EscrituraRechazada

VARIABLE_PROPIETARIOS = "INVESTIGADORES_PROPIETARIOS"
VARIABLE_INVESTIGADORES = "INVESTIGADORES_AUTORIZADOS"


def _normalizar(correo: str) -> str:
    return (correo or "").strip().lower()


def propietarios_configurados() -> frozenset[str]:
    """Núcleo inamovible definido exclusivamente por la variable nueva."""
    return frozenset(
        normalizado
        for fragmento in os.environ.get(VARIABLE_PROPIETARIOS, "").replace(";", ",").split(",")
        if (normalizado := _normalizar(fragmento))
    )


def investigadores_configurados() -> frozenset[str]:
    """Correos configurados, exactos tras recortar y pasar a minúsculas."""
    # La variable anterior se conserva durante la transición de despliegue. La
    # nueva nombra la semántica real: estas cuentas son el núcleo inamovible;
    # los investigadores delegados viven en PostgreSQL y sí se pueden revocar.
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
    """Sólo la lista de propietarios es inamovible; la heredada no lo es."""
    return _normalizar(correo) in propietarios_configurados()


def sincronizar_rol_configurado(*, roles, sujeto_google: str, correo: str) -> None:
    """Asegura el rol persistente de una cuenta declarada en el entorno.

    No abre una autorización alternativa: escribe por el bootstrap del puerto
    y después las operaciones siguen exigiendo la fila vigente. Una colisión
    por dos inicios simultáneos sólo se acepta si al releer ya existe el rol.
    """
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
    """Hace el bootstrap y traduce una caída del almacén a un resultado explícito."""
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
