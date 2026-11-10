"""Persistencia y auditoría atómica de reportes de usuario."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_persona,
    exigir_sin_supresion,
)
from dominio.puertos.almacen import EscrituraRechazada, ReferenciaDesconocida
from dominio.puertos.reportes import Reporte

ESTADOS = frozenset({"nuevo", "en_revision", "resuelto", "descartado"})


def _desde_fila(fila, *, con_reportante: bool = False) -> Reporte:
    base = fila[:14]
    reportante = None
    if con_reportante:
        nombre, correo = fila[14:16]
        reportante = {"nombre": nombre or "Cuenta institucional", "correo": correo}
    return Reporte(*base, reportante=reportante)


_CAMPOS = """
    r.id, r.reportado_por, r.rol_reportante, r.categoria, r.titulo,
    r.descripcion, r.pasos, r.ruta, r.estado, (r.captura IS NOT NULL),
    COALESCE(r.captura_bytes, 0), r.respuesta, r.creado_en, r.actualizado_en
"""


class AdaptadorReportesPostgres(RepositorioPostgres):
    def crear(  # noqa: PLR0913 -- campos explícitos del formulario
        self, *, actor: str, rol: str, categoria: str, titulo: str,
        descripcion: str, pasos: str, ruta: str, captura: bytes | None,
    ) -> Reporte:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, actor)
            exigir_sin_supresion(cur, actor)
            cur.execute(
                "SELECT count(*) FROM reporte_usuario "
                "WHERE reportado_por = %s AND creado_en >= now() - interval '24 hours'",
                (actor,),
            )
            if int(cur.fetchone()[0]) >= 5:
                raise EscrituraRechazada("alcanzaste el límite de cinco reportes en 24 horas")
            huella = hashlib.sha256(captura).hexdigest() if captura else None
            cur.execute(
                f"""
                INSERT INTO reporte_usuario (
                    reportado_por, rol_reportante, categoria, titulo, descripcion,
                    pasos, ruta, captura, captura_tipo, captura_sha256, captura_bytes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {_CAMPOS.replace('r.', '')}
                """,  # noqa: S608 -- campos constantes
                (
                    actor, rol, categoria, titulo, descripcion, pasos, ruta,
                    captura, "image/webp" if captura else None,
                    huella, len(captura) if captura else None,
                ),
            )
            reporte = _desde_fila(cur.fetchone())
            anotar(
                cur, "reporte.usuario_creado", actor=actor, sujeto_afectado=actor,
                detalle={
                    "reporte": reporte.identificador, "categoria": categoria,
                    "ruta": ruta, "con_captura": captura is not None,
                },
            )
        return reporte

    def mios(self, actor: str) -> tuple[Reporte, ...]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM reporte_usuario r "
                "WHERE r.reportado_por = %s ORDER BY r.creado_en DESC, r.id DESC LIMIT 50",
                (actor,),
            )
            return tuple(_desde_fila(fila) for fila in cur.fetchall())

    def institucionales(self, actor: str, estado: str = "") -> tuple[Reporte, ...]:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            anotar(
                cur, "reporte.institucional_consultado", actor=actor,
                detalle={"estado": estado or "todos", "limite": 100},
            )
            cur.execute(
                f"""
                SELECT {_CAMPOS}, p.nombre, p.correo
                  FROM reporte_usuario r
                  JOIN persona p ON p.sujeto_google = r.reportado_por
                 WHERE (%s = '' OR r.estado = %s)
                 ORDER BY r.creado_en DESC, r.id DESC LIMIT 100
                """,  # noqa: S608 -- campos constantes
                (estado, estado),
            )
            return tuple(_desde_fila(fila, con_reportante=True) for fila in cur.fetchall())

    def captura_propia(self, actor: str, reporte: int) -> bytes | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT captura FROM reporte_usuario WHERE id = %s AND reportado_por = %s",
                (reporte, actor),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("el reporte no existe")
            return bytes(fila[0]) if fila[0] is not None else None

    def captura(self, actor: str, reporte: int) -> bytes | None:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            anotar(
                cur, "reporte.captura_consultada", actor=actor,
                detalle={"reporte": reporte},
            )
            cur.execute("SELECT captura FROM reporte_usuario WHERE id = %s", (reporte,))
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("el reporte no existe")
            return bytes(fila[0]) if fila[0] is not None else None

    def actualizar(
        self, actor: str, reporte: int, *, estado: str, respuesta: str,
    ) -> Reporte:
        if estado not in ESTADOS:
            raise ValueError("estado de reporte no admisible")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            cur.execute(
                "SELECT estado FROM reporte_usuario WHERE id = %s FOR UPDATE", (reporte,)
            )
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("el reporte no existe")
            anterior = fila[0]
            resuelto = estado in {"resuelto", "descartado"}
            cur.execute(
                f"""
                UPDATE reporte_usuario
                   SET estado = %s, respuesta = %s, actualizado_en = now(),
                       resuelto_por = %s, resuelto_en = %s
                 WHERE id = %s
                RETURNING {_CAMPOS.replace('r.', '')}
                """,  # noqa: S608 -- campos constantes
                (
                    estado, respuesta, actor if resuelto else None,
                    datetime.now(UTC) if resuelto else None, reporte,
                ),
            )
            actualizado = _desde_fila(cur.fetchone())
            anotar(
                cur, "reporte.estado_actualizado", actor=actor,
                sujeto_afectado=actualizado.reportado_por,
                detalle={
                    "reporte": reporte, "antes": {"estado": anterior},
                    "despues": {"estado": estado}, "con_respuesta": bool(respuesta),
                },
            )
        return actualizado
