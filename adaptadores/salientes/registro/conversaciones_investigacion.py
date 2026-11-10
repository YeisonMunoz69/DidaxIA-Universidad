"""Lectura institucional auditada; no ejecuta ni reanaliza turnos."""

from __future__ import annotations

from contextlib import contextmanager

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import (
    FILTRO_PERSONA_SIN_SUPRESION_SQL,
    exigir_sin_supresion,
)
from adaptadores.salientes.registro.historial import (
    MENSAJE_TITULABLE_SQL,
    AdaptadorHistorialPostgres,
)
from dominio.puertos.almacen import AlmacenNoConfigurado


def alcance_mensajes(sujeto, clase, desde, hasta):
    """Intervalo semiabierto y matrícula histórica, nunca la matrícula actual."""
    condiciones = ["h.identificador_sujeto = %s", "h.contexto_de_uso = 'aprendizaje_estudiante'"]
    valores = [sujeto]
    if desde is not None:
        condiciones.append("h.momento >= %s")
        valores.append(desde)
    if hasta is not None:
        condiciones.append("h.momento < %s")
        valores.append(hasta)
    if clase:
        condiciones.append("""EXISTS (SELECT 1 FROM clase_matricula_historial m
            WHERE m.estudiante = h.identificador_sujeto AND m.clase = %s
              AND h.momento >= m.desde AND (m.hasta IS NULL OR h.momento < m.hasta))""")
        valores.append(clase)
    return " AND ".join(condiciones), tuple(valores)


class ConversacionesInvestigacionPostgres(AdaptadorHistorialPostgres):
    @contextmanager
    def _transaccion(self):
        if not self._cadena:
            raise AlmacenNoConfigurado('no hay base de conversaciones configurada')
        with super()._transaccion() as cnx:
            yield cnx

    @staticmethod
    def _autorizar(cur, actor):
        exigir_investigador_administrador(cur, actor)
        exigir_sin_supresion(cur, actor)

    def directorio(self, actor, *, buscar="", clase="", pagina=1, incluir_pruebas=False):
        with self._transaccion() as cnx, cnx.cursor() as cur:
            self._autorizar(cur, actor)
            anotar(cur, "investigacion.directorio_consultado", actor=actor,
                   detalle={"pagina": pagina, "clase": clase, "incluye_pruebas": incluir_pruebas})
            filtro = f"""(%s OR NOT COALESCE(p.es_cuenta_prueba, false))
                AND (position(lower(%s) in lower(p.nombre)) > 0
                     OR position(lower(%s) in lower(p.correo)) > 0)
                AND EXISTS (SELECT 1 FROM clase_matricula_historial m
                    WHERE m.estudiante = p.sujeto_google AND (%s = '' OR m.clase = %s))
                AND {FILTRO_PERSONA_SIN_SUPRESION_SQL}"""
            valores = (incluir_pruebas, buscar, buscar, clase, clase)
            cur.execute(f"SELECT count(*) FROM persona p WHERE {filtro}", valores)  # noqa: S608
            total = cur.fetchone()[0]
            cur.execute(f"""SELECT p.sujeto_google, p.nombre, p.correo,
                    COALESCE(p.es_cuenta_prueba, false)
                FROM persona p WHERE {filtro}
                ORDER BY lower(p.nombre), p.sujeto_google LIMIT 20 OFFSET %s""",  # noqa: S608
                (*valores, (pagina - 1) * 20))
            estudiantes = [dict(zip(("id", "nombre", "correo", "prueba"), fila, strict=True))
                           for fila in cur.fetchall()]
            cur.execute("SELECT id, nombre, archivada_en IS NOT NULL FROM clase ORDER BY nombre, id")
            clases = [dict(zip(("id", "nombre", "archivada"), fila, strict=True)) for fila in cur.fetchall()]
        return {"estudiantes": estudiantes, "clases": clases, "total": total,
                "pagina": pagina, "paginas": (total + 19) // 20}

    def conversaciones(self, actor, sujeto, *, clase="", desde=None, hasta=None, pagina=1):
        condicion, valores = alcance_mensajes(sujeto, clase, desde, hasta)
        with self._transaccion() as cnx, cnx.cursor() as cur:
            self._autorizar(cur, actor)
            exigir_sin_supresion(cur, sujeto)
            anotar(cur, "investigacion.conversaciones_listadas", actor=actor,
                   sujeto_afectado=sujeto, detalle={"clase": clase, "pagina": pagina})
            cur.execute(f"SELECT count(DISTINCT identificador_sesion) FROM historial_turno h WHERE {condicion}", valores)  # noqa: S608
            total = cur.fetchone()[0]
            cur.execute(f"""SELECT identificador_sesion, min(momento), max(momento),
                    count(DISTINCT turno),
                    (array_agg(contenido ORDER BY id) FILTER (WHERE autor = 'estudiante'))[1],
                    {MENSAJE_TITULABLE_SQL}
                FROM historial_turno h WHERE {condicion}
                GROUP BY identificador_sesion ORDER BY max(momento) DESC, identificador_sesion
                LIMIT 50 OFFSET %s""",  # noqa: S608
                (*valores, (pagina - 1) * 50))
            filas = cur.fetchall()
        return ([dict(zip(("sesion", "inicio", "ultimo", "turnos", "primer_mensaje", "mensaje_para_titulo"),
                          fila, strict=True)) for fila in filas],
                total)

    def conversacion(self, actor, sujeto, sesion, *, clase="", desde=None, hasta=None):
        condicion, valores = alcance_mensajes(sujeto, clase, desde, hasta)
        with self._transaccion() as cnx, cnx.cursor() as cur:
            self._autorizar(cur, actor)
            exigir_sin_supresion(cur, sujeto)
            anotar(cur, "investigacion.conversacion_consultada", actor=actor,
                   sujeto_afectado=sujeto, detalle={"conversacion": sesion, "clase": clase,
                       "desde": desde.isoformat() if desde else None,
                       "hasta": hasta.isoformat() if hasta else None})
            return self._hilo_de_cursor(cur, "h.identificador_sesion = %s AND " + condicion,
                                        (sesion, *valores))
