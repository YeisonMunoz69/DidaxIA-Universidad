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

if TYPE_CHECKING:
    from collections.abc import Iterator

class AdaptadorSolicitudesDocentesPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar

        with conectar(self._cadena) as cnx:
            yield cnx

    def _solicitud_desde_fila(self, fila) -> Solicitud:
        identificador, correo, creada, estado, nota = fila
        return Solicitud(
            identificador=identificador, correo=correo,
            creada=creada.isoformat(timespec="seconds"), estado=estado, nota=nota,
        )

    def solicitar(self, correo: str) -> Solicitud:
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
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "UPDATE solicitud_docente SET nota = %s WHERE id = %s AND estado = %s",
                (mensaje, identificador, ESTADO_PENDIENTE),
            )
            afectadas = cur.rowcount
            cnx.commit()
        return afectadas > 0

    def aprobada(self, correo: str) -> bool:
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
