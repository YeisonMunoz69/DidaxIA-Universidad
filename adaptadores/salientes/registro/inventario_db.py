from __future__ import annotations

from typing import Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres
from dominio.puertos.inventario_de_datos import Autoridad, InventarioPorTitular


_POR_SUJETO = (
    ("perfil_afectivo", False),
    ("perfil_conceptual", False),
    ("perfil_estrategico", False),
    ("registro_turno", False),
    ("historial_turno", True),

    ("evento_telemetria", False),
)


_POR_SUJETO_GOOGLE = (
    ("recurso_respuesta", True),
    ("recurso_visita", False),
    ("preferencia_interfaz", False),
    ("persona", False),
    ("consentimiento_evento", False),
    ("asentimiento_evento", False),
    ("representante_evidencia", False),
    ("rol_asignacion", False),
    ("solicitud_supresion", False),
)


OPERACION_INVENTARIO = "inventario.consultado"


class AdaptadorInventarioPostgres(RepositorioPostgres):

    def inventariar(self, sujeto_google: str, *, actor: str = "") -> InventarioPorTitular:
        with self._escritura() as cnx, cnx.cursor() as cur:
            if actor:
                anotar(
                    cur,
                    OPERACION_INVENTARIO,
                    actor=actor,
                    sujeto_afectado=sujeto_google,

                    detalle={},
                )
            autoridades = [
                *self._tablas_por_columna(cur, sujeto_google, _POR_SUJETO, "identificador_sujeto"),
                *self._tablas_por_columna(
                    cur, sujeto_google, _POR_SUJETO_GOOGLE, "sujeto_google"
                ),
                self._matriculas(cur, sujeto_google),
                self._clases_creadas(cur, sujeto_google),
                self._historial_cuerpo(cur, sujeto_google, "historial_bloque"),
                self._historial_cuerpo(cur, sujeto_google, "historial_cita"),
                self._historial_cuerpo(cur, sujeto_google, "analisis_conductual"),
                *self._tablas_por_columna(
                    cur, sujeto_google, (("relectura_conductual_trabajo", False),), "actor"
                ),
                self._revisiones(cur, sujeto_google),
                self._registro_forense(cur, sujeto_google),
                self._cola_de_revision(),
                self._navegador(),
            ]
        return InventarioPorTitular(sujeto_google=sujeto_google, autoridades=tuple(autoridades))

    def _contar(self, cur: Any, sql: str, parametros: tuple) -> int:
        cur.execute(sql, parametros)
        return cur.fetchone()[0]

    def _tablas_por_columna(
        self, cur: Any, sujeto: str, tablas: tuple, columna: str
    ) -> list[Autoridad]:
        salida = []
        for tabla, texto_libre in tablas:

            filas = self._contar(
                cur,
                f"SELECT count(*) FROM {tabla} WHERE {columna} = %s",
                (sujeto,),
            )
            salida.append(Autoridad(nombre=tabla, filas=filas, texto_libre=texto_libre))
        return salida

    def _matriculas(self, cur: Any, sujeto: str) -> Autoridad:
        filas = self._contar(
            cur, "SELECT count(*) FROM clase_matricula WHERE identificador = %s", (sujeto,)
        )
        return Autoridad(nombre="clase_matricula", filas=filas)

    def _clases_creadas(self, cur: Any, sujeto: str) -> Autoridad:
        filas = self._contar(cur, "SELECT count(*) FROM clase WHERE creador = %s", (sujeto,))
        return Autoridad(
            nombre="clase (creadas)",
            filas=filas,
            alcanzable=False,
            nota="borrarlas afectaría a terceros matriculados; decisión de V-B",
        )

    def _historial_cuerpo(self, cur: Any, sujeto: str, tabla: str) -> Autoridad:
        filas = self._contar(
            cur,
            f"SELECT count(*) FROM {tabla} b "
            "JOIN historial_turno h ON h.id = b.historial "
            "WHERE h.identificador_sujeto = %s",
            (sujeto,),
        )
        return Autoridad(nombre=tabla, filas=filas, texto_libre=True)

    def _revisiones(self, cur: Any, sujeto: str) -> Autoridad:
        filas = self._contar(
            cur, "SELECT count(*) FROM representante_revision WHERE revisada_por = %s", (sujeto,)
        )
        return Autoridad(
            nombre="representante_revision (como revisor)",
            filas=filas,
            alcanzable=False,
            nota="evidencia de quién aprobó una autorización; deber de conservación",
        )

    def _registro_forense(self, cur: Any, sujeto: str) -> Autoridad:
        filas = self._contar(
            cur,
            "SELECT count(*) FROM registro_turno WHERE identificador_sujeto = %s AND "
            "coalesce(btrim(ruta_archivo), '') <> ''",
            (sujeto,),
        )
        return Autoridad(
            nombre="registro forense (archivos en volumen)",
            filas=filas,
            alcanzable=False,
            nota="la cascada llega a registro_turno y no al archivo; brecha de Fase 2",
        )

    def _cola_de_revision(self) -> Autoridad:
        return Autoridad(
            nombre="cola_revision",
            filas=0,
            texto_libre=True,
            alcanzable=False,
            nota="no tiene clave de sujeto: no se puede contar ni alcanzar por titular",
        )

    def _navegador(self) -> Autoridad:
        return Autoridad(
            nombre="navegador (sessionStorage)",
            filas=0,
            texto_libre=True,
            alcanzable=False,
            nota="fuera del alcance del servidor; contradice EQ-007 y sigue pendiente",
        )
