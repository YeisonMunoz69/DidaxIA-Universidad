from __future__ import annotations

import secrets
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from dominio.puertos.supervision import (
    ESTADO_APROBADO,
    ESTADO_EDITADO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    AclaracionDocente,
    ItemDeRevision,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dominio.puertos.supervision import NuevoItem

class AdaptadorColaDeRevisionPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar

        with conectar(self._cadena) as cnx:
            yield cnx

    def _item_desde_fila(self, fila) -> ItemDeRevision:
        (identificador, recibido, urgencia, clase, tipo, mensaje, turno,
         estado, concepcion_candidata, ansiedad_estimada, estudiante, sesion) = fila
        return ItemDeRevision(
            identificador=identificador,
            recibido=recibido.isoformat(timespec="seconds"),
            urgencia=urgencia,
            clase=clase,
            tipo=tipo,
            mensaje=mensaje,
            turno=turno,
            estado=estado,
            concepcion_candidata=concepcion_candidata,
            ansiedad_estimada=ansiedad_estimada,
            estudiante=estudiante or "",
            sesion=sesion or "",
        )

    def agregar(self, nuevo: NuevoItem) -> ItemDeRevision:
        from psycopg.types.json import Jsonb

        identificador = secrets.token_urlsafe(8)
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cola_revision (
                    id, urgencia, clase, tipo, mensaje, turno,
                    concepcion_candidata, ansiedad_estimada, estudiante, sesion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, recibido, urgencia, clase, tipo, mensaje, turno,
                          estado, concepcion_candidata, ansiedad_estimada,
                          estudiante, sesion
                """,
                (
                    identificador, nuevo.urgencia, nuevo.clase, nuevo.tipo,
                    nuevo.mensaje, Jsonb(nuevo.turno),
                    nuevo.concepcion_candidata, nuevo.ansiedad_estimada,
                    nuevo.estudiante or None, nuevo.sesion or None,
                ),
            )
            fila = cur.fetchone()
            cnx.commit()
        return self._item_desde_fila(fila)

    def listar_pendientes(
        self,
        urgencia: str = "",
        clase: str = "",
        tipo: str = "",
        tope: int | None = None,
        desde: int = 0,
        clases_permitidas: tuple[str, ...] = (),
    ) -> list[ItemDeRevision]:
        condiciones = ["estado = %s"]
        parametros: list[Any] = [ESTADO_PENDIENTE]
        if clases_permitidas:
            condiciones.append("clase = ANY(%s)")
            parametros.append(list(clases_permitidas))
        if urgencia:
            condiciones.append("urgencia = %s")
            parametros.append(urgencia)
        if clase:
            condiciones.append("clase = %s")
            parametros.append(clase)
        if tipo:
            condiciones.append("tipo = %s")
            parametros.append(tipo)
        consulta = (
            "SELECT id, recibido, urgencia, clase, tipo, mensaje, turno, "
            "estado, concepcion_candidata, ansiedad_estimada, estudiante, sesion "
            "FROM cola_revision "
            "WHERE " + " AND ".join(condiciones) + " ORDER BY recibido"
        )
        if tope is not None:
            consulta += " LIMIT %s OFFSET %s"
            parametros.append(tope)
            parametros.append(desde)
        elif desde:

            consulta += " OFFSET %s"
            parametros.append(desde)
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(consulta, tuple(parametros))
            filas = cur.fetchall()
        return [self._item_desde_fila(fila) for fila in filas]

    def total_pendientes(
        self, urgencia: str = "", clase: str = "", tipo: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> int:
        return len(self.listar_pendientes(
            urgencia, clase, tipo, clases_permitidas=clases_permitidas
        ))

    def aprobar(
        self, identificador: str, actor: str = "", clases_permitidas: tuple[str, ...] = ()
    ) -> bool:
        return self._resolver(identificador, ESTADO_APROBADO, actor, clases_permitidas)

    def editar(
        self, identificador: str, texto: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        from psycopg.types.json import Jsonb

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT turno, clase, estudiante, sesion FROM cola_revision "
                "WHERE id = %s AND estado = %s",
                (identificador, ESTADO_PENDIENTE),
            )
            fila = cur.fetchone()
            if fila is None:
                return False
            turno, clase, estudiante, sesion = fila
            if clases_permitidas and clase not in clases_permitidas:
                return False
            if not clase or not estudiante or not sesion or not actor:
                return False
            turno = {**turno, "editado_por_docente": texto}
            cur.execute(
                "INSERT INTO aclaracion_docente "
                "(cola, clase, estudiante, sesion, docente, texto, turno) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (cola) DO NOTHING",
                (
                    identificador, clase, estudiante, sesion, actor, texto,
                    str(turno.get("turno") or "") or None,
                ),
            )
            if cur.rowcount != 1:
                return False
            cur.execute(
                "UPDATE cola_revision SET turno = %s, estado = %s, "
                "resuelto_por = %s, resuelto_en = now() WHERE id = %s",
                (Jsonb(turno), ESTADO_EDITADO, actor, identificador),
            )
            cnx.commit()
        return True

    def rechazar(
        self, identificador: str, motivo: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        from psycopg.types.json import Jsonb

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT turno, clase, estudiante, sesion FROM cola_revision "
                "WHERE id = %s AND estado = %s",
                (identificador, ESTADO_PENDIENTE),
            )
            fila = cur.fetchone()
            if fila is None:
                return False
            turno, clase, estudiante, sesion = fila
            if clases_permitidas and clase not in clases_permitidas:
                return False
            if not clase or not estudiante or not sesion or not actor:
                return False
            turno = {**turno, "motivo_de_rechazo": motivo}
            cur.execute(
                "INSERT INTO aclaracion_docente "
                "(cola, clase, estudiante, sesion, docente, texto, turno) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (cola) DO NOTHING",
                (
                    identificador, clase, estudiante, sesion, actor, motivo,
                    str(turno.get("turno") or "") or None,
                ),
            )
            if cur.rowcount != 1:
                return False
            cur.execute(
                "UPDATE cola_revision SET turno = %s, estado = %s, "
                "resuelto_por = %s, resuelto_en = now() WHERE id = %s",
                (Jsonb(turno), ESTADO_RECHAZADO, actor or None, identificador),
            )
            cnx.commit()
        return True

    def _resolver(
        self, identificador: str, estado: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        with self._conexion() as cnx, cnx.cursor() as cur:
            condiciones = "id = %s AND estado = %s"
            parametros: list[Any] = [identificador, ESTADO_PENDIENTE]
            if clases_permitidas:
                condiciones += " AND clase = ANY(%s)"
                parametros.append(list(clases_permitidas))
            cur.execute(
                "UPDATE cola_revision SET estado = %s, resuelto_por = %s, "
                f"resuelto_en = now() WHERE {condiciones}",
                (estado, actor or None, *parametros),
            )
            afectadas = cur.rowcount
            cnx.commit()
        return afectadas > 0

    def listar_aclaraciones(self, estudiante: str, sesion: str) -> list[AclaracionDocente]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT id, sesion, texto, docente, creada_en, turno "
                "FROM aclaracion_docente WHERE estudiante = %s AND sesion = %s "
                "ORDER BY id",
                (estudiante, sesion),
            )
            return [
                AclaracionDocente(
                    identificador=str(identificador), sesion=sesion_fila,
                    texto=texto, docente=docente,
                    creada_en=creada_en.isoformat(timespec="seconds"), turno=turno or "",
                )
                for identificador, sesion_fila, texto, docente, creada_en, turno in cur.fetchall()
            ]
