from __future__ import annotations

import os
from typing import TYPE_CHECKING

from adaptadores.salientes.registro.solicitudes_docente_memoria import (
    AdaptadorSolicitudesDocentesMemoria,
)
from dominio.puertos.rol_docente import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADA,
    Solicitud,
)

if TYPE_CHECKING:
    from dominio.puertos.rol_docente import PuertoSolicitudesDocentes

__all__ = [
    "ESTADO_APROBADA",
    "ESTADO_PENDIENTE",
    "ESTADO_RECHAZADA",
    "VARIABLE_LISTA_MANUAL",
    "RegistroDeDocentes",
    "Solicitud",
]


VARIABLE_LISTA_MANUAL = "DOCENTES_AUTORIZADOS"


def _normalizar(correo: str) -> str:
    return (correo or "").strip().lower()

def _lista_manual() -> frozenset[str]:
    correos = os.environ.get(VARIABLE_LISTA_MANUAL, "")
    return frozenset(
        normalizado for c in correos.split(",") if (normalizado := _normalizar(c))
    )

class RegistroDeDocentes:

    def __init__(self, adaptador_solicitudes: PuertoSolicitudesDocentes | None = None) -> None:
        self._manual = _lista_manual()
        self._adaptador: PuertoSolicitudesDocentes = (
            adaptador_solicitudes
            if adaptador_solicitudes is not None
            else AdaptadorSolicitudesDocentesMemoria()
        )

    def es_de_la_lista_manual(self, correo: str) -> bool:
        return _normalizar(correo) in self._manual

    def es_docente(self, correo: str) -> bool:
        correo_norm = _normalizar(correo)
        if self.es_de_la_lista_manual(correo_norm):
            return True
        return self._adaptador.aprobada(correo_norm)

    def solicitar(self, correo: str) -> Solicitud:
        return self._adaptador.solicitar(_normalizar(correo))

    def listar_pendientes(self) -> list[Solicitud]:
        return self._adaptador.listar_pendientes()

    def aprobar(self, identificador: str) -> bool:
        return self._adaptador.aprobar(identificador)

    def rechazar(self, identificador: str, motivo: str) -> bool:
        return self._adaptador.rechazar(identificador, motivo)

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        return self._adaptador.pedir_mas_informacion(identificador, mensaje)
