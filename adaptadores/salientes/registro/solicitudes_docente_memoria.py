from __future__ import annotations

import secrets
from datetime import UTC, datetime

from dominio.puertos.rol_docente import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADA,
    Solicitud,
)


class AdaptadorSolicitudesDocentesMemoria:

    def __init__(self) -> None:
        self._solicitudes: dict[str, Solicitud] = {}

    def solicitar(self, correo: str) -> Solicitud:
        correo_norm = correo.strip().lower()
        existente = next(
            (
                s
                for s in self._solicitudes.values()
                if s.correo == correo_norm and s.estado == ESTADO_PENDIENTE
            ),
            None,
        )
        if existente is not None:
            return existente
        solicitud = Solicitud(
            identificador=secrets.token_urlsafe(8),
            correo=correo_norm,
            creada=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        self._solicitudes[solicitud.identificador] = solicitud
        return solicitud

    def listar_pendientes(self) -> list[Solicitud]:
        pendientes = [s for s in self._solicitudes.values() if s.estado == ESTADO_PENDIENTE]
        pendientes.sort(key=lambda s: s.creada)
        return pendientes

    def aprobar(self, identificador: str) -> bool:
        return self._resolver(identificador, ESTADO_APROBADA)

    def rechazar(self, identificador: str, motivo: str) -> bool:
        solicitud = self._solicitudes.get(identificador)
        if solicitud is None or solicitud.estado != ESTADO_PENDIENTE:
            return False
        solicitud.nota = motivo
        solicitud.estado = ESTADO_RECHAZADA
        return True

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        solicitud = self._solicitudes.get(identificador)
        if solicitud is None or solicitud.estado != ESTADO_PENDIENTE:
            return False
        solicitud.nota = mensaje
        return True

    def aprobada(self, correo: str) -> bool:
        correo_norm = correo.strip().lower()
        return any(
            s.correo == correo_norm and s.estado == ESTADO_APROBADA
            for s in self._solicitudes.values()
        )

    def _resolver(self, identificador: str, estado: str) -> bool:
        solicitud = self._solicitudes.get(identificador)
        if solicitud is None or solicitud.estado != ESTADO_PENDIENTE:
            return False
        solicitud.estado = estado
        return True
