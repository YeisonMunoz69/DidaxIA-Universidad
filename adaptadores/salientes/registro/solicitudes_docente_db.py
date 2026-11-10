"""
solicitudes_docente_db.py — Persistencia de solicitudes de rol docente (`D-16` C)

La mitad de `RegistroDeDocentes` (`adaptadores/entrantes/http/docentes.py`)
que necesita almacén — la lista manual sigue en `DOCENTES_AUTORIZADOS`, sin
cambios; esto solo cubre la cola de solicitud y aprobación.
`RegistroDeDocentes` no se reemplaza entero: recibe un
`PuertoSolicitudesDocentes` en el constructor y le delega esos métodos — ver
su docstring sobre por qué las dos mitades no se tratan igual.

El respaldo sin base es `solicitudes_docente_memoria.py`, que satisface el
mismo puerto.

Reconstruye `Solicitud` de `dominio/puertos/rol_docente.py` por la misma
razón que `clases_db.py` reconstruye `Clase`/`Matricula`: duplicarlo
arriesgaría que `como_elemento()` divergiera entre las dos mitades. Hasta la
Fase 2 · sesión 3 el tipo se importaba de `entrantes/http/docentes.py`,
porque «no hay una versión de dominio del tipo»; ahora la hay y es neutral.
"""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from dominio.puertos.rol_docente import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADA,
    Solicitud,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator


class AdaptadorSolicitudesDocentesPostgres:
    """Los seis métodos de `PuertoSolicitudesDocentes`, incluido
    `aprobada()` — lo que `es_docente()` necesita y que en memoria es un
    `any()` sobre las solicitudes guardadas."""

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with conectar(self._cadena) as cnx:
            yield cnx

    def _solicitud_desde_fila(self, fila) -> Solicitud:
        identificador, correo, creada, estado, nota = fila
        return Solicitud(
            identificador=identificador, correo=correo,
            creada=creada.isoformat(timespec="seconds"), estado=estado, nota=nota,
        )

    def solicitar(self, correo: str) -> Solicitud:
        """Reutiliza la pendiente si ya existe una — mismo contrato que la
        versión en memoria: pedirlo dos veces seguidas no duplica la cola."""
        correo_norm = correo.strip().lower()
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT id, correo, creada, estado, nota FROM solicitud_docente "
                "WHERE correo = %s AND estado = %s LIMIT 1",
                (correo_norm, ESTADO_PENDIENTE),
            )
            fila = cur.fetchone()
            if fila is not None:
                return self._solicitud_desde_fila(fila)

            identificador = secrets.token_urlsafe(8)
            cur.execute(
                """
                INSERT INTO solicitud_docente (id, correo) VALUES (%s, %s)
                RETURNING id, correo, creada, estado, nota
                """,
                (identificador, correo_norm),
            )
            fila = cur.fetchone()
            cnx.commit()
        return self._solicitud_desde_fila(fila)

    def listar_pendientes(self) -> list[Solicitud]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT id, correo, creada, estado, nota FROM solicitud_docente "
                "WHERE estado = %s ORDER BY creada",
                (ESTADO_PENDIENTE,),
            )
            filas = cur.fetchall()
        return [self._solicitud_desde_fila(fila) for fila in filas]

    def aprobar(self, identificador: str) -> bool:
        return self._resolver(identificador, ESTADO_APROBADA)

    def rechazar(self, identificador: str, motivo: str) -> bool:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "UPDATE solicitud_docente SET estado = %s, nota = %s "
                "WHERE id = %s AND estado = %s",
                (ESTADO_RECHAZADA, motivo, identificador, ESTADO_PENDIENTE),
            )
            afectadas = cur.rowcount
            cnx.commit()
        return afectadas > 0

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        """La solicitud sigue pendiente — solo gana una nota. Mismo contrato
        que la versión en memoria: no es un tercer estado de resolución."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "UPDATE solicitud_docente SET nota = %s WHERE id = %s AND estado = %s",
                (mensaje, identificador, ESTADO_PENDIENTE),
            )
            afectadas = cur.rowcount
            cnx.commit()
        return afectadas > 0

    def aprobada(self, correo: str) -> bool:
        """Lo que `RegistroDeDocentes.es_docente()` necesita: si hay alguna
        solicitud aprobada para este correo, entre los dos mecanismos de
        `D-16` opción C."""
        correo_norm = correo.strip().lower()
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM solicitud_docente WHERE correo = %s AND estado = %s)",
                (correo_norm, ESTADO_APROBADA),
            )
            (existe,) = cur.fetchone()
        return bool(existe)

    def _resolver(self, identificador: str, estado: str) -> bool:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "UPDATE solicitud_docente SET estado = %s WHERE id = %s AND estado = %s",
                (estado, identificador, ESTADO_PENDIENTE),
            )
            afectadas = cur.rowcount
            cnx.commit()
        return afectadas > 0
