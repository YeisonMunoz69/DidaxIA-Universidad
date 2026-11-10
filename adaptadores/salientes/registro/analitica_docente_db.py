"""Lectura PostgreSQL de KPI descriptivos para una clase autorizada."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import traducir_fallo
from adaptadores.salientes.registro.estado_vigente_db import AdaptadorEstadoVigentePostgres
from adaptadores.salientes.registro.kpi_consultas import ConsultasKPI, alcance_sql
from adaptadores.salientes.registro.lectura_factores import completar_trazas
from adaptadores.salientes.registro.lectura_trazas_anteproyecto import leer_trazas
from adaptadores.salientes.registro.roles_db import SUJETOS_PROFESIONALES_VIGENTES_SQL
from dominio.kpi import catalogo as cat
from dominio.kpi import medidas
from dominio.kpi.contratos import ContextoDeCalculo, Periodo
from dominio.kpi.dimensiones.conductual import CONTINUACION_OBSERVABLE
from dominio.modelo.acceso import calcular_acceso, permite_escritura_longitudinal
from dominio.modelo.cobertura_evidencia import calcular_cobertura_evidencia
from dominio.modelo.factores_agregados import calcular_factores, resumir_factores
from dominio.modelo.fenomenos_anteproyecto import indicadores_individuales, resumir_trazas
from dominio.modelo.identidad import (
    MAYORIA_DE_EDAD,
    exigir_edad_admisible,
    exigir_semestre_admisible,
)
from dominio.modelo.indicios_observables import resumir_lenguaje
from dominio.modelo.menores import PLAZO_REPRESENTANTE_DIAS
from dominio.modelo.observables_dialogo import calcular_observables, resumir_observables
from dominio.modelo.oferta_academica import exigir_oferta_valida

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator


def _indicadores_anteproyecto(consultas, indicios, clase, inicio, hasta, desde):
    registros, faltantes = leer_trazas(consultas.trazas_anteproyecto())
    periodo = Periodo(desde=inicio if inicio < hasta else desde, hasta=hasta)
    oficiales = indicadores_individuales(
        indicios, resumir_trazas(registros), periodo.como_json(), clase, faltantes,
    )
    resumen = resumir_observables(consultas.mensajes_observables(), registros,
                                 periodo.desde, periodo.hasta, faltantes)
    contexto = ContextoDeCalculo(periodo, datetime.now(UTC), {"clase": clase})
    factores = resumir_factores(completar_trazas(consultas.factores_hibridos()), desde=periodo.desde, hasta=periodo.hasta)
    return [*(r.como_json() for r in calcular_factores(factores, contexto, individual=True)),
            *oficiales, *(r.como_json() for r in calcular_observables(resumen, contexto, individual=True))]


class AdaptadorAnaliticaDocentePostgres:
    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with traducir_fallo(), conectar(self._cadena) as cnx:
            yield cnx

    def directorio_de_estudiantes(
        self,
        actor: str,
        pagina: int,
        tamano: int,
        *,
        alcance_institucional: bool = False,
        buscar: str = "",
    ) -> dict:
        """Directorio mínimo para abrir fichas sin enumerar fuera del rol."""
        desplazamiento = (pagina - 1) * tamano
        with self._conexion() as cnx, cnx.cursor() as cur:
            if alcance_institucional:
                exigir_investigador_administrador(cur, actor)
                condicion = "WHERE c.archivada_en IS NULL AND NOT COALESCE(p.es_cuenta_prueba, false)"
                parametros_alcance: tuple[str, ...] = ()
            else:
                condicion = "WHERE c.creador = %s AND c.archivada_en IS NULL AND NOT COALESCE(p.es_cuenta_prueba, false)"
                parametros_alcance = (actor,)

            if buscar and alcance_institucional:
                termino = buscar.strip().lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
                literal = termino.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                condicion += """ AND (
                    translate(lower(COALESCE(p.nombre, '')), 'áéíóúüñ', 'aeiouun') LIKE %s
                    OR lower(COALESCE(p.correo, '')) LIKE %s
                )"""
                parametros_alcance += (f"%{literal}%", f"%{literal}%")

            cur.execute(
                f"""
                SELECT COUNT(*)
                  FROM clase_matricula m
                  JOIN clase c ON c.id = m.clase
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                  {condicion}
                """,  # noqa: S608 — sólo concatena una cláusula constante
                parametros_alcance,
            )
            total = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT m.identificador, m.desde, c.id, c.nombre,
                       COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante'),
                       COALESCE(NULLIF(btrim(p.foto_perfil_referencia), ''), '') <> '',
                       COALESCE(p.facultad, ''), COALESCE(p.programa, ''), p.semestre
                  FROM clase_matricula m
                  JOIN clase c ON c.id = m.clase
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                  {condicion}
                 ORDER BY translate(
                            lower(COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante')),
                            'áéíóúüñ', 'aeiouun'
                          ), m.identificador
                 LIMIT %s OFFSET %s
                """,  # noqa: S608 — sólo concatena una cláusula constante
                (*parametros_alcance, tamano, desplazamiento),
            )
            estudiantes = [
                {
                    "identificador": identificador,
                    "desde": desde.isoformat(),
                    "nombre": nombre,
                    "tiene_foto": tiene_foto,
                    "facultad": facultad,
                    "programa": programa,
                    "semestre": semestre,
                    "clase": {"id": clase, "nombre": nombre_clase},
                }
                for (
                    identificador, desde, clase, nombre_clase, nombre, tiene_foto,
                    facultad, programa, semestre,
                ) in cur.fetchall()
            ]
            anotar(
                cur,
                "consultar_directorio_estudiantes",
                actor=actor,
                detalle={
                    "alcance": "institucional" if alcance_institucional else "clases_propias",
                    "pagina": pagina,
                    "tamano": tamano,
                    "incluye_texto": False,
                    "busqueda_aplicada": bool(buscar and alcance_institucional),
                },
            )
            cnx.commit()

        return {
            "version": "directorio.estudiantes.v1",
            "pagina": pagina,
            "tamano": tamano,
            "total": total,
            "paginas": (total + tamano - 1) // tamano,
            "estudiantes": estudiantes,
        }

    def resumen_de_clase(
        self, clase: str, docente: str, desde: datetime, hasta: datetime
    ) -> dict | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT nombre FROM clase WHERE id = %s AND creador = %s "
                "AND archivada_en IS NULL",
                (clase, docente),
            )
            fila_clase = cur.fetchone()
            if fila_clase is None:
                return None

            parametros = (clase, desde, hasta)
            cur.execute(
                """
                WITH miembros AS (
                    SELECT m.identificador, m.desde
                      FROM clase_matricula m
                      LEFT JOIN persona p ON p.sujeto_google = m.identificador
                     WHERE m.clase = %s
                       AND NOT COALESCE(p.es_cuenta_prueba, false)
                ),
                filas AS (
                    SELECT h.id, h.identificador_sujeto AS sujeto,
                           h.identificador_sesion AS sesion, h.turno,
                           h.momento, h.autor, h.contexto_de_uso,
                           h.degradado, h.procedencia_origen,
                           EXISTS (
                               SELECT 1 FROM historial_material m
                                WHERE m.historial = h.id AND m.relacion = 'recuperado'
                           ) AS material,
                           EXISTS (
                               SELECT 1 FROM historial_bloque b
                                WHERE b.historial = h.id AND b.sello = 'verificado'
                           ) AS verificado,
                           EXISTS (
                               SELECT 1 FROM historial_bloque b
                                WHERE b.historial = h.id AND b.sello = 'generado'
                           ) AS generado
                      FROM historial_turno h
                      JOIN miembros m ON m.identificador = h.identificador_sujeto
                     WHERE h.momento >= %s AND h.momento < %s
                       AND h.momento >= m.desde
                ),
                turnos AS (
                    SELECT sujeto, sesion, turno, MIN(momento) AS momento,
                           BOOL_OR(autor = 'estudiante') AS hay_estudiante,
                           BOOL_OR(autor = 'sistema') AS hay_sistema,
                           COUNT(*) FILTER (WHERE autor = 'estudiante') AS filas_estudiante,
                           COUNT(*) FILTER (WHERE autor = 'sistema') AS filas_sistema,
                           BOOL_OR(autor = 'sistema' AND degradado) AS degradado,
                           BOOL_OR(autor = 'sistema' AND procedencia_origen = 'sin-fuente')
                               AS sin_fuente,
                           BOOL_OR(autor = 'sistema' AND material) AS con_material,
                           BOOL_OR(autor = 'sistema' AND verificado) AS con_verificado,
                           BOOL_OR(autor = 'sistema' AND generado) AS con_generado,
                           BOOL_AND(contexto_de_uso = 'aprendizaje_estudiante') AS educativo
                      FROM filas
                     GROUP BY sujeto, sesion, turno
                )
                SELECT
                    (SELECT COUNT(*) FROM miembros) AS matriculados,
                    COUNT(*) FILTER (WHERE educativo) AS turnos,
                    COUNT(*) FILTER (WHERE educativo AND hay_sistema) AS respuestas,
                    COUNT(DISTINCT sujeto) FILTER (WHERE educativo AND hay_estudiante)
                        AS estudiantes_activos,
                    COUNT(DISTINCT (sujeto, sesion)) FILTER (WHERE educativo)
                        AS conversaciones,
                    COUNT(*) FILTER (WHERE educativo AND degradado) AS degradados,
                    COUNT(*) FILTER (WHERE educativo AND sin_fuente) AS sin_fuente,
                    COUNT(*) FILTER (WHERE educativo AND con_material) AS con_material,
                    COUNT(*) FILTER (WHERE educativo AND con_verificado) AS con_verificado,
                    COUNT(*) FILTER (WHERE educativo AND con_generado) AS con_generado,
                    COUNT(*) FILTER (
                        WHERE educativo AND (NOT hay_estudiante OR NOT hay_sistema)
                    ) AS incompletos,
                    COUNT(*) FILTER (
                        WHERE educativo AND (filas_estudiante > 1 OR filas_sistema > 1)
                    ) AS voces_repetidas,
                    MAX(momento) FILTER (WHERE educativo) AS ultima_actividad
                  FROM turnos
                """,
                parametros,
            )
            fila = cur.fetchone()
            (
                matriculados, turnos, respuestas, activos, conversaciones,
                degradados, sin_fuente, con_material, con_verificado,
                con_generado, incompletos, voces_repetidas, ultima_actividad,
            ) = fila

            cur.execute(
                """
                WITH miembros AS (
                    SELECT m.identificador, m.desde FROM clase_matricula m
                      LEFT JOIN persona p ON p.sujeto_google = m.identificador
                     WHERE m.clase = %s
                       AND NOT COALESCE(p.es_cuenta_prueba, false)
                ),
                educativos AS (
                    SELECT h.id, h.identificador_sujeto AS sujeto,
                           h.identificador_sesion AS sesion, h.turno
                      FROM historial_turno h
                      JOIN miembros m ON m.identificador = h.identificador_sujeto
                     WHERE h.momento >= %s AND h.momento < %s
                       AND h.momento >= m.desde
                       AND h.autor = 'sistema'
                       AND h.contexto_de_uso = 'aprendizaje_estudiante'
                )
                SELECT m.obra,
                       COUNT(DISTINCT (e.sujeto, e.sesion, e.turno)) AS turnos,
                       COUNT(DISTINCT m.fragmento) AS fragmentos
                  FROM educativos e
                  JOIN historial_material m ON m.historial = e.id
                 WHERE m.relacion = 'recuperado'
                 GROUP BY m.obra
                 ORDER BY turnos DESC, m.obra
                """,
                parametros,
            )
            material = [
                {"obra": obra, "turnos": cantidad, "fragmentos": fragmentos}
                for obra, cantidad, fragmentos in cur.fetchall()
            ]

        participacion = (activos / matriculados) if matriculados else None
        return {
            "version": "kpi.v1",
            "clase": {"id": clase, "nombre": fila_clase[0]},
            "periodo": {
                "desde": desde.isoformat(), "hasta": hasta.isoformat(),
                "intervalo": "[desde,hasta)", "zona_horaria": "America/Bogota",
            },
            "alcance": {
                "contexto": "aprendizaje_estudiante",
                "atribucion": "cohorte_actual_desde_matricula",
                "incluye_consulta_profesional": False,
            },
            "actividad": {
                "matriculados": matriculados,
                "estudiantes_con_actividad": activos,
                "turnos_registrados": turnos,
                "respuestas_registradas": respuestas,
                "conversaciones": conversaciones,
                "participacion_observada": participacion,
                "ultima_actividad": ultima_actividad.isoformat() if ultima_actividad else None,
            },
            "respuesta": {
                "degradados": degradados, "sin_fuente": sin_fuente,
                "con_material_recuperado": con_material,
                "con_algun_bloque_verificado": con_verificado,
                "con_algun_bloque_generado": con_generado,
            },
            "material_por_obra": material,
            "temas": {"estado": "no_instrumentado", "elementos": []},
            "cobertura": {
                "turnos_historial_incompleto": incompletos,
                "turnos_voces_repetidas": voces_repetidas,
                "atribucion_historica_disponible": False,
                "confianza_inferencial": None,
            },
            # Compatibilidad con la primera forma consumida por la vista.
            "turnos": turnos,
            "sin_fuente": sin_fuente,
            "degradados": degradados,
        }

    def ficha_de_estudiante(
        self,
        clase: str,
        docente: str,
        estudiante: str,
        desde: datetime,
        hasta: datetime,
        actor_auditoria: str | None = None,
    ) -> dict | None:
        """Ficha individual descriptiva, autorizada por clase y auditada.

        No devuelve texto de conversaciones. Recalcula indicios observables
        sobre el periodo y la matrícula; no presenta el último estado afectivo
        longitudinal como si perteneciera a cualquier ventana seleccionada.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            if actor_auditoria is not None:
                exigir_investigador_administrador(cur, actor_auditoria)
            cur.execute(
                """
                SELECT c.nombre, m.desde,
                       COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante'),
                       COALESCE(NULLIF(btrim(p.foto_perfil_referencia), ''), '') <> '',
                       COALESCE(p.facultad, ''), COALESCE(p.programa, ''), p.semestre,
                       p.edad_declarada
                  FROM clase c
                  JOIN clase_matricula m
                    ON m.clase = c.id AND m.identificador = %s
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                 WHERE c.id = %s AND c.creador = %s AND c.archivada_en IS NULL
                   AND NOT COALESCE(p.es_cuenta_prueba, false)
                """,
                (estudiante, clase, docente),
            )
            alcance = cur.fetchone()
            if alcance is None:
                return None
            (
                nombre_clase, matriculado_desde, nombre_estudiante, tiene_foto,
                facultad, programa, semestre, edad,
            ) = alcance
            anotar(
                cur,
                "consultar_ficha_estudiante",
                actor=actor_auditoria or docente,
                sujeto_afectado=estudiante,
                detalle={"clase": clase, "incluye_texto": False},
            )
            inicio = max(desde, matriculado_desde)
            parametros = (estudiante, inicio, hasta)
            cur.execute(
                """
                WITH filas AS (
                    SELECT identificador_sesion AS sesion, turno, momento,
                           autor, contexto_de_uso, degradado, procedencia_origen
                      FROM historial_turno
                     WHERE identificador_sujeto = %s
                       AND momento >= %s AND momento < %s
                ),
                turnos AS (
                    SELECT sesion, turno, MIN(momento) AS momento,
                           BOOL_OR(autor = 'estudiante') AS hay_estudiante,
                           BOOL_OR(autor = 'sistema') AS hay_sistema,
                           BOOL_OR(autor = 'sistema' AND degradado) AS degradado,
                           BOOL_OR(
                               autor = 'sistema' AND procedencia_origen = 'sin-fuente'
                           ) AS sin_fuente,
                           BOOL_AND(contexto_de_uso = 'aprendizaje_estudiante') AS educativo
                      FROM filas
                     GROUP BY sesion, turno
                )
                SELECT COUNT(*) FILTER (WHERE educativo),
                       COUNT(*) FILTER (WHERE educativo AND hay_sistema),
                       COUNT(DISTINCT sesion) FILTER (WHERE educativo),
                       COUNT(DISTINCT (momento AT TIME ZONE 'America/Bogota')::date)
                           FILTER (WHERE educativo),
                       COUNT(*) FILTER (WHERE educativo AND degradado),
                       COUNT(*) FILTER (WHERE educativo AND sin_fuente),
                       COUNT(*) FILTER (
                           WHERE educativo AND hay_sistema
                             AND NOT degradado AND NOT sin_fuente
                       ),
                       MAX(momento) FILTER (WHERE educativo)
                  FROM turnos
                """,
                parametros,
            )
            (
                turnos, respuestas, conversaciones, dias_activos,
                degradados, sin_fuente, respuestas_validas, ultima_actividad,
            ) = cur.fetchone()
            cur.execute(
                """
                WITH turnos AS (
                    SELECT identificador_sesion AS sesion, turno,
                           MIN(momento) AS momento,
                           BOOL_AND(contexto_de_uso = 'aprendizaje_estudiante') AS educativo
                      FROM historial_turno
                     WHERE identificador_sujeto = %s
                       AND momento >= %s AND momento < %s
                     GROUP BY identificador_sesion, turno
                )
                SELECT sesion, MIN(momento), MAX(momento), COUNT(*)
                  FROM turnos
                 WHERE educativo
                 GROUP BY sesion
                 ORDER BY MAX(momento) DESC
                 LIMIT 12
                """,
                parametros,
            )
            hilos = [
                {
                    "sesion": sesion,
                    "inicio": primero.isoformat(),
                    "ultimo": ultimo.isoformat(),
                    "turnos": cantidad,
                }
                for sesion, primero, ultimo, cantidad in cur.fetchall()
            ]
            condicion, valores_alcance = alcance_sql(clase, docente, {})
            consultas = ConsultasKPI(
                cur, condicion + " AND m.estudiante = %s",
                [*valores_alcance, estudiante], (inicio, hasta), {},
            )
            vigente = AdaptadorEstadoVigentePostgres(self._cadena).desde_cursor(cur, estudiante)
            permite_indicios = (
                edad is not None and edad >= MAYORIA_DE_EDAD
                and vigente is not None
                and permite_escritura_longitudinal(calcular_acceso(vigente))
            )
            indicios = consultas.indicios_lexicos() if permite_indicios else resumir_lenguaje(())
            if not permite_indicios:
                indicios.update(estado="no_habilitado", motivo="No hay habilitación vigente para el análisis conductual individual.")
            indicadores_anteproyecto = _indicadores_anteproyecto(
                consultas, indicios, clase, inicio, hasta, desde,
            ) if permite_indicios else []
            continuacion = consultas.continuacion()
            # Un filtro anterior a la matrícula es válido pero vacío. La
            # consulta ya devuelve cero filas; no construir un periodo inverso.
            periodo_ficha = Periodo(desde=inicio if inicio < hasta else desde, hasta=hasta)
            contexto_kpi = ContextoDeCalculo(
                periodo=periodo_ficha, calculado_en=datetime.now(UTC),
                filtros={"clase": clase},
            )
            medida_continuacion = medidas.proporcion(
                CONTINUACION_OBSERVABLE,
                contexto_kpi,
                (continuacion["continuadas"], continuacion["elegibles"]),
            ).como_json()
            medida_continuacion["detalle"] = {"censuradas": continuacion["censuradas"], "ventana_horas": 24}
            indicios["observables"] = [medida_continuacion]
            referencias = consultas.referencias_conceptuales()
            medida_referencias = medidas.proporcion(
                cat.buscar("recuperacion.referencias_conceptuales"), contexto_kpi,
                (referencias["con_referencia"], referencias["elegibles"]),
            ).como_json()
            recuperacion = consultas.recuperacion()
            niveles = consultas.niveles()
            indicadores_actividad = [
                medidas.proporcion(
                    cat.buscar("recuperacion.cobertura"), contexto_kpi,
                    (recuperacion["con_material"], recuperacion["elegibles"]),
                ).como_json(),
                medidas.proporcion(
                    cat.buscar("aprendizaje.escalamiento_de_ayuda"), contexto_kpi,
                    (niveles["escalados"], niveles["con_nivel"]),
                    faltantes=niveles["sin_nivel"],
                ).como_json(),
                medida_referencias,
            ]
            if permite_indicios:
                sin_retorno = consultas.sin_retorno_7d()
                medida_retorno = medidas.proporcion(
                    cat.buscar("conductual.abandono_de_conversacion"), contexto_kpi,
                    (sin_retorno["sin_retorno"], sin_retorno["elegibles"]),
                ).como_json()
                medida_retorno["detalle"] = {
                    "censuradas": sin_retorno["censuradas"], "ventana_dias": 7,
                }
                indicios["observables"].append(medida_retorno)
            rectificaciones = []
            if actor_auditoria is not None:
                cur.execute(
                    """
                    SELECT r.id, r.valor_anterior, r.valor_nuevo, r.registrada_en,
                           r.motivo, r.efecto_consentimiento, r.efecto_asentimiento,
                           r.reconsentimiento_necesario, t.estado, t.momento
                      FROM rectificacion_edad r
                      JOIN LATERAL (
                          SELECT estado, momento
                            FROM rectificacion_edad_transicion
                           WHERE rectificacion = r.id
                           ORDER BY momento DESC, id DESC LIMIT 1
                      ) t ON true
                     WHERE r.sujeto_google = %s
                     ORDER BY r.registrada_en DESC, r.id DESC
                     LIMIT 20
                    """,
                    (estudiante,),
                )
                rectificaciones = [
                    {
                        "id": secuencia,
                        "valor_anterior": anterior,
                        "valor_nuevo": nuevo,
                        "registrada_en": registrada.isoformat(),
                        "motivo": motivo,
                        "efecto_consentimiento": efecto_consentimiento,
                        "efecto_asentimiento": efecto_asentimiento,
                        "reconsentimiento_necesario": reconsentimiento,
                        "estado": estado,
                        "estado_en": estado_en.isoformat(),
                    }
                    for (
                        secuencia, anterior, nuevo, registrada, motivo,
                        efecto_consentimiento, efecto_asentimiento, reconsentimiento,
                        estado, estado_en,
                    ) in cur.fetchall()
                ]
            # ``anotar()`` forma parte del mismo resultado observable que la
            # ficha. Sin este commit la lectura llegaba al navegador, pero el
            # cierre de la conexión podía descartar silenciosamente la
            # auditoría, justo lo contrario de una consulta institucional.
            cnx.commit()

        cobertura_evidencia = calcular_cobertura_evidencia(
            turnos_elegibles=turnos,
            conversaciones=conversaciones,
            dias_activos=dias_activos,
            respuestas=respuestas,
            respuestas_validas=respuestas_validas,
            ultima_actividad=ultima_actividad,
            hasta=hasta,
        )
        resultado = {
            "version": "ficha.v1",
            "clase": {"id": clase, "nombre": nombre_clase},
            "estudiante": {
                "identificador": estudiante,
                "nombre": nombre_estudiante,
                "desde": matriculado_desde.isoformat(),
                "tiene_foto": tiene_foto,
                "facultad": facultad,
                "programa": programa,
                "semestre": semestre,
            },
            "periodo": periodo_ficha.como_json(),
            "actividad": {
                "turnos_registrados": turnos,
                "respuestas_registradas": respuestas,
                "conversaciones": conversaciones,
                "dias_con_actividad": dias_activos,
                "ultima_actividad": (
                    ultima_actividad.isoformat() if ultima_actividad else None
                ),
            },
            "respuesta": {"degradados": degradados, "sin_fuente": sin_fuente},
            "cobertura_evidencia": cobertura_evidencia,
            "conversaciones": hilos,
            "indicios_conductuales": indicios,
            "indicadores_anteproyecto": indicadores_anteproyecto,
            "referencias_conceptuales": medida_referencias,
            "indicadores_actividad": indicadores_actividad,
            "conceptual": {"estado": "no_instrumentado", "elementos": []},
            "estrategico": {"estado": "no_instrumentado", "elementos": []},
        }
        if actor_auditoria is not None:
            resultado["estudiante"]["edad"] = edad
            resultado["rectificaciones_edad"] = rectificaciones
        return resultado


    def actividad_de_clase(  # noqa: C901, PLR0912, PLR0913, PLR0915 — recorrido preexistente; no se modifica en esta entrega.
        self,
        clase: str,
        actor: str,
        desde: datetime,
        hasta: datetime,
        *,
        metrica: str = "turnos",
        busqueda: str = "",
        solo_activos: bool = False,
        limite: int = 200,
        alcance_institucional: bool = False,
    ) -> dict | None:
        """Actividad comparativa de una clase en una consulta, sin texto libre."""
        metricas = {
            "turnos": "turnos_elegibles",
            "conversaciones": "conversaciones",
            "dias": "dias_activos",
            "recencia": "ultima_actividad",
            "cobertura": "cobertura_evidencia",
        }
        if metrica not in metricas:
            raise ValueError("métrica de actividad no admitida")
        limite = max(1, min(int(limite), 500))
        punto_medio = desde + (hasta - desde) / 2
        with self._conexion() as cnx, cnx.cursor() as cur:
            if alcance_institucional:
                exigir_investigador_administrador(cur, actor)
                cur.execute("SELECT nombre FROM clase WHERE id = %s AND archivada_en IS NULL", (clase,))
            else:
                cur.execute(
                    "SELECT nombre FROM clase WHERE id = %s AND creador = %s "
                    "AND archivada_en IS NULL",
                    (clase, actor),
                )
            fila_clase = cur.fetchone()
            if fila_clase is None:
                return None
            cur.execute(
                f"""
                WITH miembros AS (
                    SELECT m.identificador, m.desde,
                           COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante') AS nombre,
                           COALESCE(NULLIF(btrim(p.foto_perfil_referencia), ''), '') <> ''
                               AS tiene_foto
                      FROM clase_matricula m
                      LEFT JOIN persona p ON p.sujeto_google = m.identificador
                      WHERE m.clase = %s
                        AND NOT COALESCE(p.es_cuenta_prueba, false)
                        AND m.identificador NOT IN (
                            {SUJETOS_PROFESIONALES_VIGENTES_SQL}
                        )
                ),
                filas AS (
                    SELECT h.identificador_sujeto AS sujeto,
                           h.identificador_sesion AS sesion, h.turno,
                           h.momento, h.autor, h.contexto_de_uso,
                           h.degradado, h.procedencia_origen
                      FROM historial_turno h
                      JOIN miembros m ON m.identificador = h.identificador_sujeto
                     WHERE h.momento >= %s AND h.momento < %s
                       AND h.momento >= m.desde
                ),
                turnos AS (
                    SELECT sujeto, sesion, turno, MIN(momento) AS momento,
                           BOOL_OR(autor = 'estudiante') AS hay_estudiante,
                           BOOL_OR(autor = 'sistema') AS hay_sistema,
                           BOOL_OR(autor = 'sistema' AND degradado) AS degradado,
                           BOOL_OR(
                               autor = 'sistema' AND procedencia_origen = 'sin-fuente'
                           ) AS sin_fuente,
                           BOOL_AND(contexto_de_uso = 'aprendizaje_estudiante') AS educativo
                      FROM filas
                     GROUP BY sujeto, sesion, turno
                ),
                validos AS (
                    SELECT * FROM turnos
                     WHERE educativo AND hay_estudiante AND hay_sistema
                )
                SELECT m.identificador, m.nombre, m.tiene_foto,
                       COUNT(v.turno) AS turnos,
                       COUNT(DISTINCT v.sesion) AS conversaciones,
                       COUNT(DISTINCT (v.momento AT TIME ZONE 'America/Bogota')::date)
                           AS dias_activos,
                       MAX(v.momento) AS ultima_actividad,
                       COUNT(v.turno) FILTER (WHERE v.momento < %s) AS primera_mitad,
                       COUNT(v.turno) FILTER (WHERE v.momento >= %s) AS segunda_mitad,
                       COUNT(v.turno) FILTER (
                           WHERE NOT v.degradado AND NOT v.sin_fuente
                       ) AS respuestas_validas
                  FROM miembros m
                  LEFT JOIN validos v ON v.sujeto = m.identificador
                 GROUP BY m.identificador, m.nombre, m.tiene_foto
                """,  # noqa: S608 — interpola un subquery constante y centralizado
                (clase, desde, hasta, punto_medio, punto_medio),
            )
            filas = cur.fetchall()
            if alcance_institucional:
                anotar(
                    cur,
                    "consultar_actividad_clase",
                    actor=actor,
                    detalle={"clase": clase, "incluye_texto": False},
                )
                cnx.commit()

        estudiantes = []
        consulta = busqueda.strip().casefold()
        for (
            identificador,
            nombre,
            tiene_foto,
            turnos,
            conversaciones,
            dias_activos,
            ultima_actividad,
            primera_mitad,
            segunda_mitad,
            respuestas_validas,
        ) in filas:
            if consulta and consulta not in nombre.casefold():
                continue
            if solo_activos and not turnos:
                continue
            cobertura = calcular_cobertura_evidencia(
                turnos_elegibles=turnos,
                conversaciones=conversaciones,
                dias_activos=dias_activos,
                respuestas=turnos,
                respuestas_validas=respuestas_validas,
                ultima_actividad=ultima_actividad,
                hasta=hasta,
            )
            if segunda_mitad > primera_mitad:
                tendencia = "aumenta"
            elif segunda_mitad < primera_mitad:
                tendencia = "disminuye"
            elif turnos:
                tendencia = "estable"
            else:
                tendencia = "sin_actividad"
            estudiantes.append(
                {
                    "identificador": identificador,
                    "alias_proyeccion": "E-" + sha256(
                        f"{clase}:{identificador}".encode()
                    ).hexdigest()[:6].upper(),
                    "nombre": nombre,
                    "tiene_foto": tiene_foto,
                    "turnos_elegibles": turnos,
                    "conversaciones": conversaciones,
                    "dias_activos": dias_activos,
                    "ultima_actividad": (
                        ultima_actividad.isoformat() if ultima_actividad else None
                    ),
                    "promedio_turnos": (
                        round(turnos / conversaciones, 2) if conversaciones else None
                    ),
                    "respuestas_con_fuente": respuestas_validas,
                    "tendencia": tendencia,
                    "cobertura_evidencia": cobertura["valor"],
                    "cobertura_estado": cobertura["estado"],
                }
            )

        clave = metricas[metrica]

        def valor_orden(item: dict) -> float:
            valor = item[clave]
            if valor is None:
                return -1.0
            if isinstance(valor, str):
                return datetime.fromisoformat(valor).timestamp()
            return float(valor)

        estudiantes.sort(
            key=lambda item: (
                -valor_orden(item), item["nombre"].casefold(), item["identificador"]
            )
        )
        posicion = 0
        valor_anterior: float | None = None
        for indice, estudiante in enumerate(estudiantes, start=1):
            valor = valor_orden(estudiante)
            if valor_anterior is None or valor != valor_anterior:
                posicion = indice
                valor_anterior = valor
            estudiante["posicion"] = posicion

        total = len(estudiantes)
        estudiantes = estudiantes[:limite]
        actualizado = datetime.now(hasta.tzinfo).isoformat()
        return {
            "version": "actividad-clase.v1",
            "clase": {"id": clase, "nombre": fila_clase[0]},
            "periodo": {
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "intervalo": "[desde,hasta)",
            },
            "metrica": metrica,
            "actualizado_en": actualizado,
            "total": total,
            "limite": limite,
            "truncado": total > limite,
            "incluye_texto": False,
            "estudiantes": estudiantes,
        }

    def corregir_perfil_de_estudiante(
        self,
        clase: str,
        actor: str,
        estudiante: str,
        datos_academicos: dict,
        *,
        alcance_institucional: bool = False,
    ) -> dict | None:
        """Corrige datos académicos sin abrir la edad ni la identidad de Google.

        La autorización, la matrícula, el cambio y su auditoría comparten una
        transacción. Para el docente se exige propiedad de la clase; para el
        investigador, su asignación administrativa vigente.
        """
        facultad, programa = exigir_oferta_valida(
            datos_academicos.get("facultad"), datos_academicos.get("programa")
        )
        semestre = datos_academicos.get("semestre")
        exigir_semestre_admisible(semestre)
        with self._conexion() as cnx, cnx.cursor() as cur:
            if alcance_institucional:
                exigir_investigador_administrador(cur, actor)
                cur.execute(
                    """
                    SELECT 1 FROM clase_matricula
                     WHERE clase = %s AND identificador = %s
                    """,
                    (clase, estudiante),
                )
            else:
                cur.execute(
                    """
                    SELECT 1
                      FROM clase c
                      JOIN clase_matricula m
                        ON m.clase = c.id AND m.identificador = %s
                     WHERE c.id = %s AND c.creador = %s
                    """,
                    (estudiante, clase, actor),
                )
            if cur.fetchone() is None:
                return None
            cur.execute(
                """
                UPDATE persona
                   SET facultad = %s, programa = %s, semestre = %s,
                       actualizada_en = now()
                 WHERE sujeto_google = %s
             RETURNING nombre
                """,
                (facultad, programa, semestre, estudiante),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            anotar(
                cur,
                "corregir_perfil_academico",
                actor=actor,
                sujeto_afectado=estudiante,
                detalle={
                    "clase": clase,
                    "campos": ["facultad", "programa", "semestre"],
                    "alcance": "institucional" if alcance_institucional else "clase_propia",
                },
            )
            cnx.commit()
        return {
            "identificador": estudiante,
            "nombre": fila[0] or "Estudiante",
            "facultad": facultad,
            "programa": programa,
            "semestre": semestre,
        }

    def rectificar_edad(
        self, clase: str, actor: str, estudiante: str, edad_nueva: int, motivo: str
    ) -> dict | None:
        """Rectifica edad sin reescribir actos previos y deja su máquina histórica."""
        exigir_edad_admisible(edad_nueva)
        motivo = str(motivo or "").strip()
        if len(motivo) < 8 or len(motivo) > 500:
            raise ValueError("el motivo debe tener entre 8 y 500 caracteres")
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            cur.execute(
                """
                SELECT p.edad_declarada
                  FROM persona p
                  JOIN clase_matricula m ON m.identificador = p.sujeto_google
                 WHERE p.sujeto_google = %s AND m.clase = %s
                 FOR UPDATE OF p
                """,
                (estudiante, clase),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            edad_anterior = fila[0]
            if edad_anterior is None:
                raise ValueError("sin edad anterior no hay una rectificación; falta declararla")
            if edad_anterior == edad_nueva:
                raise ValueError("la edad nueva debe ser distinta de la anterior")
            era_menor = edad_anterior < MAYORIA_DE_EDAD
            sera_menor = edad_nueva < MAYORIA_DE_EDAD
            cambia_categoria = era_menor != sera_menor
            efecto_consentimiento = (
                "reconsentimiento_por_cambio_de_categoria"
                if cambia_categoria else "sin_cambio_de_categoria"
            )
            efecto_asentimiento = (
                "pasa_a_requerir" if sera_menor and not era_menor
                else "deja_de_requerir" if era_menor and not sera_menor
                else "sin_cambio"
            )
            sustituidas: list[int] = []
            if cambia_categoria:
                cur.execute(
                    """
                    SELECT r.id
                      FROM rectificacion_edad r
                     WHERE r.sujeto_google = %s
                       AND r.reconsentimiento_necesario
                       AND EXISTS (
                           SELECT 1 FROM rectificacion_edad_transicion t
                            WHERE t.rectificacion = r.id
                              AND t.estado = 'reconsentimiento_pendiente'
                       )
                       AND NOT EXISTS (
                           SELECT 1 FROM rectificacion_edad_transicion t
                            WHERE t.rectificacion = r.id
                              AND t.estado IN ('reconsentida', 'sustituida')
                       )
                     ORDER BY r.registrada_en, r.id
                     FOR UPDATE OF r
                    """,
                    (estudiante,),
                )
                sustituidas = [int(fila[0]) for fila in cur.fetchall()]
                for anterior in sustituidas:
                    cur.execute(
                        "INSERT INTO rectificacion_edad_transicion "
                        "(rectificacion, estado, actor, motivo) VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (rectificacion, estado) DO NOTHING",
                        (
                            anterior,
                            "sustituida",
                            actor,
                            "sustituida por una rectificación posterior con cambio de categoría",
                        ),
                    )
            cur.execute(
                """
                INSERT INTO rectificacion_edad
                    (sujeto_google, valor_anterior, valor_nuevo, actor, motivo,
                     efecto_consentimiento, efecto_asentimiento,
                     reconsentimiento_necesario)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, registrada_en
                """,
                (
                    estudiante, edad_anterior, edad_nueva, actor, motivo,
                    efecto_consentimiento, efecto_asentimiento, cambia_categoria,
                ),
            )
            secuencia, registrada_en = cur.fetchone()
            cur.execute(
                """
                UPDATE persona
                   SET edad_declarada = %s,
                       representante_limite = CASE
                           WHEN %s < %s THEN now() + make_interval(days => %s)
                           ELSE representante_limite
                       END,
                       actualizada_en = now()
                 WHERE sujeto_google = %s
                """,
                (
                    edad_nueva, edad_nueva, MAYORIA_DE_EDAD,
                    PLAZO_REPRESENTANTE_DIAS, estudiante,
                ),
            )
            estados = ["registrada"]
            estados.append("reconsentimiento_pendiente" if cambia_categoria else "aplicada")
            for estado in estados:
                cur.execute(
                    "INSERT INTO rectificacion_edad_transicion "
                    "(rectificacion, estado, actor, motivo) VALUES (%s, %s, %s, %s)",
                    (secuencia, estado, actor, motivo if estado == "registrada" else ""),
                )
            anotar(
                cur, "rectificacion_edad.aplicada", actor=actor,
                sujeto_afectado=estudiante,
                detalle={
                    "rectificacion": secuencia,
                    "cambio_categoria": cambia_categoria,
                    "reconsentimiento_necesario": cambia_categoria,
                    "antes": {"edad": edad_anterior},
                    "despues": {"edad": edad_nueva},
                    "motivo": motivo,
                    "rectificaciones_sustituidas": sustituidas,
                },
            )
            cnx.commit()
        return {
            "id": secuencia,
            "valor_anterior": edad_anterior,
            "valor_nuevo": edad_nueva,
            "registrada_en": registrada_en.isoformat(),
            "motivo": motivo,
            "efecto_consentimiento": efecto_consentimiento,
            "efecto_asentimiento": efecto_asentimiento,
            "reconsentimiento_necesario": cambia_categoria,
            "estado": estados[-1],
            "rectificaciones_sustituidas": sustituidas,
        }

    def detalle_institucional_de_clase(
        self, clase: str, investigador: str, desde: datetime, hasta: datetime
    ) -> dict | None:
        """Abre una cohorte institucional sin heredar las rutas del docente."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            cur.execute("SELECT creador FROM clase WHERE id = %s AND archivada_en IS NULL", (clase,))
            fila = cur.fetchone()
            if fila is None:
                return None
            docente = fila[0]
            anotar(
                cur, "consultar_clase_institucional", actor=investigador,
                detalle={"clase": clase, "incluye_texto": False},
            )
            cur.execute(
                """
                WITH actividad AS (
                    SELECT h.identificador_sujeto AS estudiante,
                           COUNT(DISTINCT (h.identificador_sesion, h.turno)) FILTER (
                               WHERE h.contexto_de_uso = 'aprendizaje_estudiante'
                           ) AS turnos,
                           MAX(h.momento) FILTER (
                               WHERE h.contexto_de_uso = 'aprendizaje_estudiante'
                           ) AS ultima
                      FROM historial_turno h
                     WHERE h.momento >= %s AND h.momento < %s
                     GROUP BY h.identificador_sujeto
                )
                SELECT m.identificador, m.desde,
                       COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante'),
                       COALESCE(NULLIF(btrim(p.foto_perfil_referencia), ''), '') <> '',
                       COALESCE(a.turnos, 0), a.ultima,
                       COALESCE(p.facultad, ''), COALESCE(p.programa, ''), p.semestre
                  FROM clase_matricula m
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                  LEFT JOIN actividad a ON a.estudiante = m.identificador
                 WHERE m.clase = %s
                 ORDER BY p.nombre NULLS LAST, m.identificador
                """,
                (desde, hasta, clase),
            )
            estudiantes = [
                {
                    "identificador": identificador,
                    "desde": matriculado.isoformat(),
                    "nombre": nombre,
                    "tiene_foto": tiene_foto,
                    "turnos": turnos,
                    "ultima_actividad": ultima.isoformat() if ultima else None,
                    "facultad": facultad,
                    "programa": programa,
                    "semestre": semestre,
                }
                for (
                    identificador, matriculado, nombre, tiene_foto, turnos, ultima,
                    facultad, programa, semestre,
                )
                in cur.fetchall()
            ]
            cnx.commit()
        resumen = self.resumen_de_clase(clase, docente, desde, hasta)
        if resumen is None:
            return None
        return {"version": "clase.investigacion.v1", "resumen": resumen,
                "estudiantes": estudiantes}

    def ficha_institucional_de_estudiante(
        self, clase: str, investigador: str, estudiante: str,
        desde: datetime, hasta: datetime,
    ) -> dict | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            cur.execute("SELECT creador FROM clase WHERE id = %s AND archivada_en IS NULL", (clase,))
            fila = cur.fetchone()
            if fila is None:
                return None
            docente = fila[0]
        ficha = self.ficha_de_estudiante(
            clase, docente, estudiante, desde, hasta,
            actor_auditoria=investigador,
        )
        if ficha is not None:
            ficha = {**ficha, "version": "ficha.investigacion.v1",
                     "alcance_profesional": "institucional"}
        return ficha

    def resumen_institucional(
        self, investigador: str, desde: datetime, hasta: datetime
    ) -> dict:
        """Resumen de cursos y uso; autorización y auditoría comparten transacción."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            anotar(
                cur,
                "consultar_analitica_institucional",
                actor=investigador,
                detalle={
                    "catalogo": "kpi.v1",
                    "desde": desde.isoformat(),
                    "hasta": hasta.isoformat(),
                    "incluye_texto": False,
                },
            )
            cur.execute(
                """
                WITH filas AS (
                    SELECT m.clase, h.identificador_sujeto AS sujeto,
                           h.identificador_sesion AS sesion, h.turno, h.autor,
                           h.contexto_de_uso, h.degradado, h.procedencia_origen
                      FROM clase_matricula m
                      JOIN clase c ON c.id = m.clase AND c.archivada_en IS NULL
                      LEFT JOIN persona p ON p.sujeto_google = m.identificador
                      JOIN historial_turno h ON h.identificador_sujeto = m.identificador
                     WHERE h.momento >= %s AND h.momento < %s
                       AND h.momento >= m.desde
                       AND NOT COALESCE(p.es_cuenta_prueba, false)
                ),
                turnos AS (
                    SELECT clase, sujeto, sesion, turno,
                           BOOL_OR(autor = 'estudiante') AS hay_estudiante,
                           BOOL_OR(autor = 'sistema') AS hay_sistema,
                           BOOL_OR(autor = 'sistema' AND degradado) AS degradado,
                           BOOL_OR(autor = 'sistema' AND procedencia_origen = 'sin-fuente')
                               AS sin_fuente,
                           BOOL_AND(contexto_de_uso = 'aprendizaje_estudiante') AS educativo
                      FROM filas
                     GROUP BY clase, sujeto, sesion, turno
                ),
                actividad AS (
                    SELECT clase,
                           COUNT(*) FILTER (WHERE educativo) AS turnos,
                           COUNT(DISTINCT sujeto) FILTER (WHERE educativo AND hay_estudiante)
                               AS estudiantes_activos,
                           COUNT(*) FILTER (WHERE educativo AND degradado) AS degradados,
                           COUNT(*) FILTER (WHERE educativo AND sin_fuente) AS sin_fuente
                      FROM turnos GROUP BY clase
                )
                SELECT c.id, c.nombre, c.creador,
                       COALESCE(NULLIF(btrim(p.nombre), ''), 'Docente institucional'),
                       COUNT(DISTINCT m.identificador) FILTER (
                           WHERE NOT COALESCE(pe.es_cuenta_prueba, false)
                       ) AS estudiantes,
                       COALESCE(a.estudiantes_activos, 0), COALESCE(a.turnos, 0),
                       COALESCE(a.degradados, 0), COALESCE(a.sin_fuente, 0)
                  FROM clase c
                  LEFT JOIN persona p ON p.sujeto_google = c.creador
                  LEFT JOIN clase_matricula m ON m.clase = c.id
                  LEFT JOIN persona pe ON pe.sujeto_google = m.identificador
                  LEFT JOIN actividad a ON a.clase = c.id
                 WHERE c.archivada_en IS NULL
                 GROUP BY c.id, c.nombre, c.creador, p.nombre,
                          a.estudiantes_activos, a.turnos, a.degradados, a.sin_fuente
                 ORDER BY c.nombre, c.id
                """,
                (desde, hasta),
            )
            cursos = [
                {
                    "id": id_clase,
                    "nombre": nombre,
                    "docente": {"id": docente, "nombre": nombre_docente},
                    "estudiantes": estudiantes,
                    "estudiantes_con_actividad": activos,
                    "turnos": turnos,
                    "degradados": degradados,
                    "sin_fuente": sin_fuente,
                }
                for (
                    id_clase, nombre, docente, nombre_docente, estudiantes,
                    activos, turnos, degradados, sin_fuente,
                ) in cur.fetchall()
            ]
            # Drill-down institucional: sólo perfiles con facultad y programa
            # explícitos. Los incompletos siguen visibles en calidad de datos;
            # asignarlos a una categoría inventada haría que un filtro pareciera
            # más preciso de lo que los datos sostienen.
            cur.execute(
                """
                SELECT p.facultad, p.programa, c.creador,
                       COALESCE(NULLIF(btrim(pd.nombre), ''), 'Docente institucional'),
                       c.id, c.nombre, m.identificador,
                       COALESCE(NULLIF(btrim(p.nombre), ''), 'Estudiante'), p.semestre
                  FROM clase c
                  JOIN clase_matricula m ON m.clase = c.id
                  JOIN persona p ON p.sujeto_google = m.identificador
                  LEFT JOIN persona pd ON pd.sujeto_google = c.creador
                 WHERE c.archivada_en IS NULL
                   AND NOT COALESCE(p.es_cuenta_prueba, false)
                   AND NULLIF(btrim(p.facultad), '') IS NOT NULL
                   AND NULLIF(btrim(p.programa), '') IS NOT NULL
                 ORDER BY p.facultad, p.programa, pd.nombre NULLS LAST,
                          c.nombre, p.nombre NULLS LAST, m.identificador
                """
            )
            jerarquia = _armar_jerarquia(cur.fetchall())
            cur.execute(
                """SELECT contexto_de_uso, COUNT(*),
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY latencia_total_ms),
                          percentile_cont(0.95) WITHIN GROUP (ORDER BY latencia_total_ms)
                     FROM registro_turno
                    WHERE creado_en >= %s AND creado_en < %s
                    GROUP BY contexto_de_uso ORDER BY contexto_de_uso""",
                (desde, hasta),
            )
            operacion = [
                {
                    "contexto": contexto, "registros": registros,
                    "p50_suma_trazas_ms": p50, "p95_suma_trazas_ms": p95,
                }
                for contexto, registros, p50, p95 in cur.fetchall()
            ]
            cnx.commit()

        docentes = len({curso["docente"]["id"] for curso in cursos})
        # La matrícula única permite sumar sin duplicar estudiantes entre cursos.
        estudiantes = sum(curso["estudiantes"] for curso in cursos)
        return {
            "version": "investigacion.v1",
            "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "resumen": {
                "docentes": docentes, "cursos": len(cursos),
                "estudiantes": estudiantes,
                "estudiantes_con_actividad": sum(
                    curso["estudiantes_con_actividad"] for curso in cursos
                ),
                "turnos": sum(curso["turnos"] for curso in cursos),
            },
            "cursos": cursos,
            "jerarquia": jerarquia,
            "operacion": {"incluye_texto": False, "por_contexto": operacion},
            "metodologia": {
                "catalogo": "kpi.v1",
                "atribucion": "cohorte_actual_desde_matricula",
                "confianza_calibrada": None,
            },
        }


def _armar_jerarquia(filas: list[tuple]) -> dict:
    """Anida el recorrido autorizado sin ordenar a docentes por desempeño."""
    facultades: dict[str, dict] = {}
    for (
        facultad, programa, docente, nombre_docente, clase, nombre_clase,
        estudiante, nombre_estudiante, semestre,
    ) in filas:
        nodo_facultad = facultades.setdefault(
            facultad, {"nombre": facultad, "programas": {}}
        )
        nodo_programa = nodo_facultad["programas"].setdefault(
            programa, {"nombre": programa, "docentes": {}}
        )
        nodo_docente = nodo_programa["docentes"].setdefault(
            docente,
            {"identificador": docente, "nombre": nombre_docente, "clases": {}},
        )
        nodo_clase = nodo_docente["clases"].setdefault(
            clase, {"identificador": clase, "nombre": nombre_clase, "estudiantes": []}
        )
        nodo_clase["estudiantes"].append({
            "identificador": estudiante,
            "nombre": nombre_estudiante,
            "semestre": semestre,
        })

    return {
        "facultades": [
            {
                "nombre": nodo_facultad["nombre"],
                "programas": [
                    {
                        "nombre": nodo_programa["nombre"],
                        "docentes": [
                            {
                                "identificador": nodo_docente["identificador"],
                                "nombre": nodo_docente["nombre"],
                                "clases": list(nodo_docente["clases"].values()),
                            }
                            for nodo_docente in nodo_programa["docentes"].values()
                        ],
                    }
                    for nodo_programa in nodo_facultad["programas"].values()
                ],
            }
            for nodo_facultad in facultades.values()
        ]
    }
