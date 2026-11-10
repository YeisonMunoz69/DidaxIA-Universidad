from __future__ import annotations

from adaptadores.salientes.registro.cola_revision_memoria import ColaDeRevision
from dominio.puertos.supervision import (
    ESTADO_APROBADO,
    ESTADO_EDITADO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    TIPO_DEGRADADO,
    TIPO_RESPUESTA,
    TIPO_SIN_FUENTE,
    ItemDeRevision,
    NuevoItem,
    PuertoColaDeRevision,
)

__all__ = [
    "ESTADO_APROBADO",
    "ESTADO_EDITADO",
    "ESTADO_PENDIENTE",
    "ESTADO_RECHAZADO",
    "TIPO_DEGRADADO",
    "TIPO_RESPUESTA",
    "TIPO_SIN_FUENTE",
    "ColaDeRevision",
    "ItemDeRevision",
    "NuevoItem",
    "PuertoColaDeRevision",
]
