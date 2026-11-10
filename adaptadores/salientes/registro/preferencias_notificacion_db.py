from __future__ import annotations

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_persona_activa,
)
from dominio.puertos.preferencias_notificacion import CATEGORIAS, valores_predeterminados


class AdaptadorPreferenciasDeNotificacionPostgres(RepositorioPostgres):
    @staticmethod
    def _exigir_categoria(categoria: str) -> None:
        if categoria not in CATEGORIAS:
            raise ValueError("categoría de notificación no admisible")

    def consultar(self, sujeto: str) -> dict[str, bool]:
        preferencias = valores_predeterminados()
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT categoria, correo_habilitado "
                "FROM preferencia_notificacion WHERE sujeto_google = %s",
                (sujeto,),
            )
            for categoria, habilitada in cur.fetchall():
                if categoria in preferencias:
                    preferencias[categoria] = bool(habilitada)
        return preferencias

    def guardar(self, sujeto: str, categoria: str, habilitada: bool) -> dict[str, bool]:
        self._exigir_categoria(categoria)
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto)
            cur.execute(
                """
                INSERT INTO preferencia_notificacion
                    (sujeto_google, categoria, correo_habilitado, actualizado_en)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (sujeto_google, categoria) DO UPDATE
                    SET correo_habilitado = EXCLUDED.correo_habilitado,
                        actualizado_en = now()
                """,
                (sujeto, categoria, habilitada),
            )
            anotar(
                cur,
                "notificacion.preferencia_actualizada",
                actor=sujeto,
                sujeto_afectado=sujeto,
                detalle={"categoria": categoria, "correo_habilitado": habilitada},
            )
            cur.execute(
                "SELECT categoria, correo_habilitado "
                "FROM preferencia_notificacion WHERE sujeto_google = %s",
                (sujeto,),
            )
            filas = cur.fetchall()
        preferencias = valores_predeterminados()
        preferencias.update({categoria: bool(valor) for categoria, valor in filas})
        return preferencias

    def habilitada(self, sujeto: str, categoria: str) -> bool:
        self._exigir_categoria(categoria)
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT correo_habilitado FROM preferencia_notificacion "
                "WHERE sujeto_google = %s AND categoria = %s",
                (sujeto, categoria),
            )
            fila = cur.fetchone()
        return bool(fila and fila[0])

    def habilitada_para_correo(self, correo: str, categoria: str) -> bool:
        self._exigir_categoria(categoria)
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT pn.correo_habilitado
                  FROM persona p
                  JOIN preferencia_notificacion pn
                    ON pn.sujeto_google = p.sujeto_google
                 WHERE lower(p.correo) = lower(%s) AND pn.categoria = %s
                 LIMIT 1
                """,
                (correo.strip(), categoria),
            )
            fila = cur.fetchone()
        return bool(fila and fila[0])
