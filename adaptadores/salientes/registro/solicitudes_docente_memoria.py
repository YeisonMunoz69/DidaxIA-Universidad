"""
solicitudes_docente_memoria.py — La cola de solicitudes en memoria (`D-16` C)
==================================================================================

El respaldo de `AdaptadorSolicitudesDocentesPostgres`: mismo
`PuertoSolicitudesDocentes` (`dominio/puertos/rol_docente.py`), mismo modelo,
sin base. Un reinicio del backend pierde cualquier solicitud pendiente o
resuelta, y por eso `aplicacion.py` prefiere el de PostgreSQL cuando
`AGENTE_BD` está y `GET /api/salud` declara cuándo cayó a este.

Dónde vivía antes, y por qué se extrajo
----------------------------------------------
Hasta la Fase 2 · sesión 3, esta mitad era un `dict` **dentro** de
`RegistroDeDocentes` (`adaptadores/entrantes/http/docentes.py`), y cada uno de
sus cinco métodos empezaba con `if self._adaptador is not None: ... else: ...`.
Eran dos implementaciones del mismo contrato en el mismo archivo, con la de
memoria escrita a mano y la de PostgreSQL detrás de un `if`. Extraerla deja un
solo camino: `RegistroDeDocentes` **siempre** delega en un adaptador, y quien
compone decide cuál.

La lista a mano de `DOCENTES_AUTORIZADOS` **no** está aquí y no debe estarlo:
es configuración del borde, no un almacén. Ver el docstring de
`RegistroDeDocentes` y `dominio/puertos/rol_docente.py`.

Sin límite de reintentos, igual que antes
------------------------------------------------
Una solicitud rechazada se puede volver a pedir tantas veces como quiera quien
la pide, y quien modera la vuelve a ver en la cola. Un tope o un enfriamiento
sería una decisión de producto que nadie ha tomado.


"""

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
    """Los seis métodos de `PuertoSolicitudesDocentes` sobre un `dict`."""

    def __init__(self) -> None:
        self._solicitudes: dict[str, Solicitud] = {}

    def solicitar(self, correo: str) -> Solicitud:
        """Reutiliza la solicitud pendiente si ya existe una — pedirlo dos
        veces seguidas no duplica la cola. Una solicitud rechazada SÍ puede
        volver a pedirse y crea una solicitud nueva."""
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
        """Sin motivo no se llama a esto — igual que `ColaDeRevision.rechazar()`,
        la validación de que el motivo no esté vacío es del borde, no de
        este almacén."""
        solicitud = self._solicitudes.get(identificador)
        if solicitud is None or solicitud.estado != ESTADO_PENDIENTE:
            return False
        solicitud.nota = motivo
        solicitud.estado = ESTADO_RECHAZADA
        return True

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        """La tercera acción, distinta de aprobar y de rechazar: la
        solicitud SIGUE pendiente —no se resuelve—, solo gana una nota
        visible para quien la pidió. Es lo que hace posible «sin límite de
        reintentos» sin escribir código de reintento: por esta vía la
        solicitud nunca sale de la cola."""
        solicitud = self._solicitudes.get(identificador)
        if solicitud is None or solicitud.estado != ESTADO_PENDIENTE:
            return False
        solicitud.nota = mensaje
        return True

    def aprobada(self, correo: str) -> bool:
        """Lo que `RegistroDeDocentes.es_docente()` necesita: si hay alguna
        solicitud aprobada para este correo."""
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
