"""
kpi_consultas.py — El SQL del catálogo KPI v1.1, y sólo el SQL
================================================================

Este módulo devuelve **materia prima**: filas y escalares. No decide estados, no
divide y no redacta nada. Esa separación es deliberada y tiene dos motivos.

**Se puede revisar.** Quien audita una cifra necesita leer la consulta sin que
la lógica de «cuándo una muestra es insuficiente» esté entretejida con el
`GROUP BY`. Aquí está el `SELECT`; en `kpi_armado.py`, la aritmética; en
`dominio/kpi/medidas.py`, la regla.

**Se puede probar sin base.** El armado recibe diccionarios, así que la mitad
que decide estados se prueba con filas escritas a mano y la mitad que consulta
se prueba contra PostgreSQL real. Con todo junto, comprobar «una muestra de
cuatro no se publica» habría exigido sembrar cuatro estudiantes.

Por qué varias consultas devuelven filas por estudiante en vez de agregados
--------------------------------------------------------------------------------
Porque medianas, percentiles y ventanas de retorno se leen mejor en Python que
en un `percentile_cont` anidado dentro de tres CTE, y porque la población que
recorren está acotada por la matrícula: un curso son decenas y la institución
del piloto, centenares.

⚠️ El límite se declara en vez de descubrirse: si la matrícula creciera a
decenas de miles, estas consultas traerían una fila por persona y habría que
mover la agregación al motor. Hoy no compensa pagar esa complejidad.

Qué excluye TODO lo de este módulo
-------------------------------------------
El contexto `consulta_profesional` (`EQ-031`) y los turnos anteriores a la
matrícula de la persona. Las dos exclusiones viven en `_TURNOS`, una sola vez,
para que ningún indicador pueda olvidarse de una.


"""

from __future__ import annotations

from typing import Any

from dominio.kpi.definiciones import MUESTRA_MINIMA, ZONA_HORARIA
from dominio.modelo.telemetria import ORIGEN_DE, TipoDeEvento

#: La población elegible, con sus filtros. `{condicion}` la compone
#: `alcance_sql()`; nunca lleva un valor interpolado, sólo cláusulas constantes.
_POBLACION = """
matriculas AS (
    SELECT m.estudiante, m.clase, m.desde, m.hasta,
           COALESCE(p.facultad, '') AS facultad,
           COALESCE(p.programa, '') AS programa,
           p.semestre, p.edad_declarada AS edad
      FROM clase_matricula_historial m
      JOIN clase c ON c.id = m.clase
      LEFT JOIN persona p ON p.sujeto_google = m.estudiante
     WHERE {condicion}
       AND NOT COALESCE(p.es_cuenta_prueba, false)
       AND c.archivada_en IS NULL
       AND m.desde < %s
       AND (m.hasta IS NULL OR m.hasta > %s)
),
poblacion AS (
    SELECT estudiante,
           MAX(facultad) AS facultad,
           MAX(programa) AS programa,
           MAX(semestre) AS semestre,
           MAX(edad) AS edad
      FROM matriculas
     GROUP BY estudiante
)
"""

#: Un turno lógico con todo lo observable de sus dos voces.
#:
#: `educativo` usa `BOOL_AND` y no `BOOL_OR`: un turno cuyas dos voces no
#: coincidan en contexto no se cuenta como educativo. No debería ocurrir —el
#: filtro 12 escribe el mismo contexto en las dos— y si ocurriera, contarlo
#: sería agregar media conversación profesional.
_TURNOS = """
turnos AS (
    SELECT h.identificador_sujeto AS estudiante,
           mat.clase,
           h.identificador_sesion AS sesion,
           h.turno,
           MIN(h.momento) AS momento,
           MIN(h.momento) FILTER (WHERE h.autor = 'estudiante') AS pregunta_en,
           MAX(h.momento) FILTER (WHERE h.autor = 'sistema') AS respuesta_en,
           BOOL_OR(h.autor = 'estudiante') AS hay_estudiante,
           BOOL_OR(h.autor = 'sistema') AS hay_sistema,
           BOOL_AND(h.contexto_de_uso = 'aprendizaje_estudiante') AS educativo,
           BOOL_OR(h.autor = 'sistema' AND h.degradado) AS degradado,
           BOOL_OR(h.autor = 'sistema' AND h.procedencia_origen = 'sin-fuente')
               AS sin_fuente,
           MAX(h.nivel) FILTER (WHERE h.autor = 'sistema') AS nivel,
           BOOL_OR(
               h.autor = 'sistema'
               AND EXISTS (
                   SELECT 1 FROM historial_material mm
                    WHERE mm.historial = h.id AND mm.relacion = 'recuperado'
               )
           ) AS con_material
      FROM historial_turno h
      JOIN matriculas mat ON mat.estudiante = h.identificador_sujeto
     WHERE h.momento >= %s AND h.momento < %s
       AND h.momento >= mat.desde
       AND (mat.hasta IS NULL OR h.momento < mat.hasta)
       AND ({condicion_turno})
     GROUP BY h.identificador_sujeto, mat.clase, h.identificador_sesion, h.turno
),
validos AS (
    SELECT * FROM turnos
     WHERE educativo AND hay_estudiante AND hay_sistema
)
"""


def alcance_sql(clase: str | None, actor_docente: str | None, filtros: dict) -> tuple[str, list]:
    """La condición de la población y sus parámetros.

    Devuelve SQL con marcadores `%s` y la lista de valores. Ningún valor se
    interpola en el texto: lo que se concatena son cláusulas constantes, que es
    la única forma segura de componer un `WHERE` variable.

    `actor_docente` **no** es un filtro más. Cuando llega, la condición exige
    que la clase sea suya, y esa exigencia viaja dentro de la misma consulta que
    lee los datos: comprobarla antes, en otra llamada, dejaría entre la
    comprobación y la lectura el hueco que `autorizacion_sql.py` documenta.
    """
    condiciones: list[str] = ["TRUE"]
    parametros: list = []
    if clase:
        condiciones.append("c.id = %s")
        parametros.append(clase)
    if actor_docente:
        condiciones.append("c.creador = %s")
        parametros.append(actor_docente)
    if filtros.get("docente"):
        condiciones.append("c.creador = %s")
        parametros.append(filtros["docente"])
    if filtros.get("facultad"):
        condiciones.append("COALESCE(p.facultad, '') = %s")
        parametros.append(filtros["facultad"])
    if filtros.get("programa"):
        condiciones.append("COALESCE(p.programa, '') = %s")
        parametros.append(filtros["programa"])
    if filtros.get("semestre"):
        condiciones.append("p.semestre = %s")
        parametros.append(int(filtros["semestre"]))
    return " AND ".join(condiciones), parametros


def filtros_de_turno_sql(filtros: dict) -> tuple[str, list]:
    """Restricciones observables de un turno, sin interpolar valores.

    Se aplican sobre las dos voces ``h``. Las subconsultas correlacionadas
    evitan el error de filtrar sólo la voz del sistema y perder la del
    estudiante, lo que invalidaría el turno completo.
    """
    condiciones = ["TRUE"]
    parametros: list = []
    if filtros.get("concepto"):
        condiciones.append(
            """EXISTS (
                SELECT 1
                  FROM historial_turno hs
                  JOIN historial_concepto hc ON hc.historial = hs.id
                 WHERE hs.identificador_sujeto = h.identificador_sujeto
                   AND hs.turno = h.turno
                   AND hc.concepto = %s
            )"""
        )
        parametros.append(filtros["concepto"])
    for nombre, columna in (
        ("version_corpus", "version_corpus"),
        ("version_modelo", "version_modelo"),
    ):
        if filtros.get(nombre):
            condiciones.append(
                f"""EXISTS (
                    SELECT 1 FROM evento_telemetria et
                     WHERE et.tipo = 'turno.respondido'
                       AND et.identificador_sujeto = h.identificador_sujeto
                       AND et.turno = h.turno
                       AND et.{columna} = %s
                )"""  # noqa: S608 — columna sale de la tupla cerrada
            )
            parametros.append(filtros[nombre])
    return " AND ".join(condiciones), parametros


class ConsultasKPI:
    """Las nueve lecturas del catálogo, sobre un cursor de quien llama.

    Recibe el cursor y no abre nada: todas tienen que caber en la misma
    transacción que la auditoría de la lectura institucional, o la constancia y
    lo leído podrían confirmarse por separado.
    """

    def __init__(
        self, cur: Any, condicion: str, alcance: list, periodo: tuple,
        filtros: dict | None = None,
    ) -> None:
        self._cur = cur
        self._condicion = condicion
        self._alcance = alcance
        self._periodo = list(periodo)
        self._filtros = filtros or {}
        self._condicion_turno, self._parametros_turno = filtros_de_turno_sql(
            self._filtros
        )

    # ── Composición ──────────────────────────────────────────────────────────

    @property
    def _base(self) -> str:
        return (
            "WITH " + _POBLACION.format(condicion=self._condicion) + ","
            + _TURNOS.format(condicion_turno=self._condicion_turno)
        )

    def _ejecutar(self, cola: str, extra: list | None = None) -> list[tuple]:
        self._cur.execute(
            self._base + cola,  # noqa: S608 — sólo cláusulas constantes concatenadas
            [
                *self._alcance,
                self._periodo[1],
                self._periodo[0],
                *self._periodo,
                *self._parametros_turno,
                *(extra or []),
            ],
        )
        return self._cur.fetchall()

    # ── 1 · Población y actividad, una fila por estudiante ──────────────────

    def continuacion(self) -> dict:
        """Una oportunidad por hilo, 24 h completas y sin duplicar matrículas.

        Solo usa datos dentro del corte. Censura también los positivos cuya
        ventana aún no termina: evita privilegiar éxitos recientes.
        """
        filas = self._ejecutar(
            """
            , unicos AS (
                SELECT DISTINCT estudiante, sesion, turno, pregunta_en, respuesta_en
                  FROM validos
            ), primeras AS (
                SELECT DISTINCT ON (estudiante, sesion)
                       estudiante, sesion, turno, respuesta_en
                  FROM unicos WHERE respuesta_en IS NOT NULL
                 ORDER BY estudiante, sesion, respuesta_en, turno
            )
            SELECT COUNT(*) FILTER (WHERE p.respuesta_en + interval '24 hours' < %s),
                   COUNT(*) FILTER (
                       WHERE p.respuesta_en + interval '24 hours' < %s
                         AND EXISTS (
                             SELECT 1 FROM unicos u
                              WHERE u.estudiante = p.estudiante AND u.sesion = p.sesion
                                AND u.turno <> p.turno AND u.pregunta_en > p.respuesta_en
                                AND u.pregunta_en <= p.respuesta_en + interval '24 hours'
                         )
                   ),
                   COUNT(*) FILTER (WHERE p.respuesta_en + interval '24 hours' >= %s)
              FROM primeras p
            """, [self._periodo[1]] * 3,
        )
        n, x, censuradas = filas[0]
        return dict(elegibles=int(n), continuadas=int(x), censuradas=int(censuradas))

    def sin_retorno_7d(self) -> dict:
        """Hilos sin otro turno educativo en siete días tras su primera respuesta.

        La ventana se cierra dentro del corte. Un hilo sin regreso puede haber
        terminado satisfactoriamente; esta consulta no infiere la intención.
        """
        filas = self._ejecutar(
            """
            , unicos AS (
                SELECT DISTINCT estudiante, sesion, turno, pregunta_en, respuesta_en
                  FROM validos
            ), primeras AS (
                SELECT DISTINCT ON (estudiante, sesion)
                       estudiante, sesion, turno, respuesta_en
                  FROM unicos WHERE respuesta_en IS NOT NULL
                 ORDER BY estudiante, sesion, respuesta_en, turno
            )
            SELECT COUNT(*) FILTER (WHERE p.respuesta_en + interval '7 days' < %s),
                   COUNT(*) FILTER (
                       WHERE p.respuesta_en + interval '7 days' < %s
                         AND NOT EXISTS (
                             SELECT 1 FROM unicos u
                              WHERE u.estudiante = p.estudiante AND u.sesion = p.sesion
                                AND u.turno <> p.turno
                                AND u.pregunta_en > p.respuesta_en
                                AND u.pregunta_en <= p.respuesta_en + interval '7 days'
                         )
                   ),
                   COUNT(*) FILTER (WHERE p.respuesta_en + interval '7 days' >= %s)
              FROM primeras p
            """, [self._periodo[1]] * 3,
        )
        n, x, censuradas = filas[0]
        return dict(elegibles=int(n), sin_retorno=int(x), censuradas=int(censuradas))

    def referencias_conceptuales(self) -> dict:
        """Turnos completos cuya respuesta enlazó un concepto del material.

        `historial_concepto` es emitida para páginas del banco ancladas en los
        fragmentos citados. Es exposición de material, no intento ni dominio.
        """
        fila = self._ejecutar(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM historial_turno h
                       JOIN historial_concepto hc ON hc.historial = h.id
                        WHERE h.identificador_sujeto = v.estudiante
                          AND h.identificador_sesion = v.sesion
                          AND h.turno = v.turno AND h.autor = 'sistema'
                   ))
              FROM (SELECT DISTINCT estudiante, sesion, turno FROM validos) v
            """
        )[0]
        return {"elegibles": int(fila[0]), "con_referencia": int(fila[1])}

    def indicios_lexicos(self) -> dict:
        """El texto se consume localmente y nunca integra el contrato de salida."""
        from dominio.modelo.indicios_observables import resumir_lenguaje  # noqa: PLC0415

        filas = self._ejecutar(
            """
            SELECT h.contenido
              FROM historial_turno h
             WHERE h.autor = 'estudiante'
               AND h.contexto_de_uso = 'aprendizaje_estudiante'
               AND h.momento >= %s AND h.momento < %s
               AND EXISTS (
                   SELECT 1 FROM perfil_afectivo a
                    WHERE a.identificador_sujeto = h.identificador_sujeto
                      AND a.turno IN (h.turno, h.identificador_sesion)
                      AND a.alcance = 'estado'
               )
               AND EXISTS (
                   SELECT 1 FROM validos v
                    WHERE v.estudiante = h.identificador_sujeto
                      AND v.sesion = h.identificador_sesion AND v.turno = h.turno
               )
             ORDER BY h.momento, h.id
            """, list(self._periodo),
        )
        return resumir_lenguaje(fila[0] for fila in filas)

    def trazas_anteproyecto(self) -> list[dict]:
        """Referencias a trazas de turnos completos, dentro del mismo alcance."""
        filas = self._ejecutar(
            """
            SELECT v.estudiante, v.sesion, v.turno, MIN(r.ruta_archivo), MIN(v.momento)
              FROM validos v
              LEFT JOIN registro_turno r ON r.turno = v.turno
               AND r.identificador_sujeto = v.estudiante
               AND r.identificador_sesion = v.sesion
               AND r.contexto_de_uso = 'aprendizaje_estudiante'
             GROUP BY v.estudiante, v.sesion, v.turno
             ORDER BY MIN(v.momento), v.estudiante, v.sesion, v.turno
            """
        )
        return [dict(estudiante=estudiante, sesion=sesion, turno=turno, ruta=ruta,
                     momento=momento.isoformat())
                for estudiante, sesion, turno, ruta, momento in filas]

    def mensajes_observables(self) -> list[dict]:
        """Texto privado y claves para ordenar pares; no sale al contrato API."""
        filas = self._ejecutar(
            """
            SELECT DISTINCT h.identificador_sujeto, h.identificador_sesion,
                   h.turno, h.momento, h.contenido
              FROM historial_turno h
             WHERE h.autor = 'estudiante'
               AND h.contexto_de_uso = 'aprendizaje_estudiante'
               AND h.momento >= %s AND h.momento < %s
               AND EXISTS (
                   SELECT 1 FROM perfil_afectivo a
                    WHERE a.identificador_sujeto = h.identificador_sujeto
                      AND a.turno IN (h.turno, h.identificador_sesion)
                      AND a.alcance = 'estado'
               )
               AND EXISTS (
                   SELECT 1 FROM validos v
                    WHERE v.estudiante = h.identificador_sujeto
                      AND v.sesion = h.identificador_sesion AND v.turno = h.turno
               )
             ORDER BY h.momento, h.identificador_sujeto, h.identificador_sesion, h.turno
            """, list(self._periodo),
        )
        return [dict(estudiante=sujeto, sesion=sesion, turno=turno,
                     momento=momento.isoformat(), texto=texto)
                for sujeto, sesion, turno, momento, texto in filas]

    def textos_indicios(self) -> list[tuple[str, str]]:
        """Mensajes con productor afectivo histórico, sin exponer texto al API."""
        filas = self._ejecutar(
            """
            SELECT DISTINCT h.identificador_sujeto, h.id, h.contenido
              FROM validos v
              JOIN historial_turno h ON h.identificador_sujeto = v.estudiante
               AND h.identificador_sesion = v.sesion AND h.turno = v.turno
               AND h.autor = 'estudiante'
             WHERE EXISTS (
                 SELECT 1 FROM perfil_afectivo a
                  WHERE a.identificador_sujeto = h.identificador_sujeto
                    AND a.turno IN (h.turno, h.identificador_sesion)
                    AND a.alcance = 'estado'
             )
            """
        )
        return [(estudiante, contenido) for estudiante, _, contenido in filas]

    def factores_hibridos(self) -> list[dict]:
        """Lecturas y contexto anterior del mismo hilo; ningún texto se publica."""
        from dominio.modelo.factores_conductuales import VERSION  # noqa: PLC0415

        filas = self._ejecutar(
            """
            SELECT DISTINCT h.id, h.identificador_sujeto, h.identificador_sesion,
                   h.turno, h.momento, h.contenido, a.lectura, a.trazas_matematicas,
                   r.ruta_archivo, a.origen, a.analizado_en, (SELECT s.contenido FROM historial_turno s
                       WHERE s.turno=h.turno AND s.identificador_sujeto=h.identificador_sujeto
                         AND s.identificador_sesion=h.identificador_sesion AND s.autor='sistema'
                       ORDER BY s.id LIMIT 1),
                   EXISTS (SELECT 1 FROM analisis_conductual anterior
                       WHERE anterior.historial=h.id AND anterior.version<>%s)
              FROM historial_turno h
              LEFT JOIN analisis_conductual a ON a.historial=h.id AND a.version=%s
              LEFT JOIN registro_turno r ON r.turno=h.turno
                   AND r.identificador_sujeto=h.identificador_sujeto
                   AND r.identificador_sesion=h.identificador_sesion
             WHERE h.autor='estudiante' AND h.contexto_de_uso='aprendizaje_estudiante'
               AND h.momento < %s
               AND EXISTS (SELECT 1 FROM validos v WHERE v.estudiante=h.identificador_sujeto
                            AND v.sesion=h.identificador_sesion AND NOT v.degradado)
               AND EXISTS (SELECT 1 FROM matriculas m WHERE m.estudiante=h.identificador_sujeto
                            AND h.momento >= m.desde AND (m.hasta IS NULL OR h.momento < m.hasta))
               AND EXISTS (SELECT 1 FROM perfil_afectivo p WHERE p.identificador_sujeto=h.identificador_sujeto
                            AND p.turno IN (h.turno,h.identificador_sesion) AND p.alcance='estado')
               AND EXISTS (SELECT 1 FROM historial_turno s WHERE s.turno=h.turno
                   AND s.identificador_sujeto=h.identificador_sujeto
                   AND s.identificador_sesion=h.identificador_sesion AND s.autor='sistema'
                   AND NOT s.degradado AND s.contexto_de_uso='aprendizaje_estudiante')
             ORDER BY h.momento,h.id
            """, [VERSION, VERSION, self._periodo[1]],
        )
        return [dict(historial=ident, estudiante=sujeto, sesion=sesion, turno=turno,
                     momento=momento, mensaje=texto, analisis_semantico=lectura or {},
                     trazas=trazas, ruta=ruta, origen_analisis=origen, analizado_en=fecha_analisis,
                     tutor=tutor or "", lectura_anterior=anterior)
                for ident,sujeto,sesion,turno,momento,texto,lectura,trazas,ruta,origen,fecha_analisis,tutor,anterior in filas]

    def actividad_por_estudiante(self) -> list[dict]:
        """Turnos, sesiones, días locales activos y primera/última actividad.

        No recibe el final del periodo: las ventanas de retorno y de actividad
        semanal las decide el armado, que ya tiene el contexto. Recibirlo aquí
        dejaba un campo repetido en cada fila que nadie leía, y un dato duplicado
        es un dato que puede discrepar.
        """
        filas = self._ejecutar(
            f"""
            , turnos_historicos AS (
                SELECT h.identificador_sujeto AS estudiante,
                       h.identificador_sesion AS sesion,
                       h.turno,
                       MIN(h.momento) AS momento,
                       BOOL_OR(h.autor = 'estudiante') AS hay_estudiante,
                       BOOL_OR(h.autor = 'sistema') AS hay_sistema,
                       BOOL_AND(
                           h.contexto_de_uso = 'aprendizaje_estudiante'
                       ) AS educativo
                  FROM historial_turno h
                  JOIN matriculas mat
                    ON mat.estudiante = h.identificador_sujeto
                   AND h.momento >= mat.desde
                   AND (mat.hasta IS NULL OR h.momento < mat.hasta)
                   AND ({self._condicion_turno})
                 GROUP BY h.identificador_sujeto, h.identificador_sesion, h.turno
            ), primera AS (
                SELECT DISTINCT ON (estudiante) estudiante, sesion, momento
                  FROM turnos_historicos
                 WHERE educativo AND hay_estudiante AND hay_sistema
                 ORDER BY estudiante, momento, sesion
            )
            SELECT pob.estudiante,
                   COUNT(v.turno) AS turnos,
                   COUNT(DISTINCT v.sesion) AS sesiones,
                   COUNT(DISTINCT (v.momento AT TIME ZONE '{ZONA_HORARIA}')::date) AS dias,
                   MIN(pr.momento) AS primera,
                   MAX(v.momento) AS ultima,
                   BOOL_OR(
                       v.sesion IS DISTINCT FROM pr.sesion
                       AND v.momento > pr.momento
                       AND v.momento <= pr.momento + interval '7 days'
                   ) AS regreso_7,
                   BOOL_OR(
                       v.sesion IS DISTINCT FROM pr.sesion
                       AND v.momento > pr.momento
                       AND v.momento <= pr.momento + interval '30 days'
                   ) AS regreso_30,
                   MAX(pob.facultad) AS facultad,
                   MAX(pob.programa) AS programa,
                   MAX(pob.semestre) AS semestre,
                   MAX(pob.edad) AS edad
              FROM poblacion pob
              LEFT JOIN validos v ON v.estudiante = pob.estudiante
              LEFT JOIN primera pr ON pr.estudiante = pob.estudiante
             GROUP BY pob.estudiante
            """,
            extra=[*self._parametros_turno],
        )
        return [
            {
                "estudiante": f[0], "turnos": f[1], "sesiones": f[2], "dias": f[3],
                "primera": f[4], "ultima": f[5],
                "regreso_7": bool(f[6]), "regreso_30": bool(f[7]),
                "facultad": f[8] or "", "programa": f[9] or "", "semestre": f[10],
                "edad": f[11],
            }
            for f in filas
        ]

    # ── 2 · Conversaciones ──────────────────────────────────────────────────

    def conversaciones(self) -> list[dict]:
        """Una fila por sesión con turnos válidos, para profundidad e intervalos."""
        filas = self._ejecutar(
            """
            SELECT estudiante, sesion, COUNT(*) AS turnos,
                   MIN(momento) AS inicio, MAX(momento) AS fin
              FROM validos
             GROUP BY estudiante, sesion
             ORDER BY estudiante, MIN(momento)
            """
        )
        return [
            {"estudiante": f[0], "sesion": f[1], "turnos": f[2], "inicio": f[3], "fin": f[4]}
            for f in filas
        ]

    # ── 3 · Recuperación documental ─────────────────────────────────────────

    def recuperacion(self) -> dict:
        """Turnos elegibles y su relación con el material recuperado."""
        fila = self._ejecutar(
            """
            SELECT COUNT(*) AS elegibles,
                   COUNT(*) FILTER (WHERE con_material) AS con_material,
                   COUNT(*) FILTER (WHERE sin_fuente) AS sin_fuente,
                   COUNT(*) FILTER (WHERE degradado) AS degradados
              FROM validos
            """
        )[0]
        return {
            "elegibles": int(fila[0]),
            "con_material": int(fila[1]),
            "sin_fuente": int(fila[2]),
            "degradados": int(fila[3]),
        }

    def material(self) -> dict:
        """Diversidad y concentración: fragmentos, obras y reparto de apariciones."""
        filas = self._ejecutar(
            """
            SELECT m.fragmento, m.obra, COUNT(*) AS apariciones
              FROM historial_turno h
              JOIN validos v
                ON v.estudiante = h.identificador_sujeto
               AND v.sesion = h.identificador_sesion
               AND v.turno = h.turno
              JOIN historial_material m ON m.historial = h.id
             WHERE h.autor = 'sistema' AND m.relacion = 'recuperado'
             GROUP BY m.fragmento, m.obra
             ORDER BY COUNT(*) DESC, m.fragmento
            """
        )
        apariciones = [int(f[2]) for f in filas]
        return {
            "fragmentos": len(filas),
            "obras": len({f[1] for f in filas}),
            "apariciones_totales": sum(apariciones),
            "apariciones_top5": sum(apariciones[:5]),
        }

    # ── 4 · Bloques verificables ────────────────────────────────────────────

    def bloques(self) -> dict:
        """Sólo los de tipo «notacion»: los únicos que pueden sellarse verificados."""
        fila = self._ejecutar(
            """
            SELECT COUNT(*) AS verificables,
                   COUNT(*) FILTER (WHERE b.sello = 'verificado') AS verificados
              FROM historial_turno h
              JOIN validos v
                ON v.estudiante = h.identificador_sujeto
               AND v.sesion = h.identificador_sesion
               AND v.turno = h.turno
              JOIN historial_bloque b ON b.historial = h.id
             WHERE h.autor = 'sistema' AND b.tipo = 'notacion'
            """
        )[0]
        return {"verificables": int(fila[0]), "verificados": int(fila[1])}

    # ── 5 · Escalamiento de ayuda ───────────────────────────────────────────

    def niveles(self) -> dict:
        """Turnos con nivel registrado y cuántos pasaron del sondeo."""
        fila = self._ejecutar(
            """
            SELECT COUNT(*) FILTER (WHERE COALESCE(nivel, '') <> '') AS con_nivel,
                   COUNT(*) FILTER (WHERE nivel IN ('regla', 'desarrollo')) AS escalados,
                   COUNT(*) FILTER (WHERE COALESCE(nivel, '') = '') AS sin_nivel
              FROM validos
            """
        )[0]
        return {
            "con_nivel": int(fila[0]),
            "escalados": int(fila[1]),
            "sin_nivel": int(fila[2]),
        }

    # ── 6 · Supervisión ─────────────────────────────────────────────────────

    def supervision(self, clases: list[str], periodo: tuple) -> dict:
        """La cola dentro del alcance. Sin clases visibles, no hay nada que contar.

        `clases` se pasa explícito y no se deriva aquí porque el alcance de la
        cola es por clase, no por estudiante: un elemento sin estudiante
        atribuido —los anteriores a la migración 19— sigue perteneciendo a su
        clase, y contarlos exige mirar la columna que sí tienen.
        """
        if not clases:
            return {
                "revisados": 0, "aprobados": 0, "editados": 0, "rechazados": 0,
                "pendientes": 0, "mas_antiguo": None, "estudiantes_revisados": 0,
                "sin_atribucion": 0, "horas": [], "derivados": 0,
                "estudiantes_revisados_ids": [],
            }
        desde, hasta = periodo
        self._cur.execute(
            """
            SELECT estado, recibido, resuelto_en, estudiante
             FROM cola_revision
             WHERE clase = ANY(%s)
               AND recibido < %s
            """,
            (clases, hasta),
        )
        filas = self._cur.fetchall()
        # Una decisión pertenece al periodo en que se resolvió, aunque hubiera
        # llegado antes. La carga pendiente es una fotografía al cierre, por lo
        # que incluye lo recibido antes de ``desde`` que seguía abierto.
        resueltos = [
            f for f in filas
            if f[2] is not None and desde <= f[2] < hasta
        ]
        pendientes_al_cierre = [f for f in filas if f[2] is None or f[2] >= hasta]
        estudiantes_revisados = {f[3] for f in resueltos if f[3]}
        horas = [
            (f[2] - f[1]).total_seconds() / 3600
            for f in resueltos
            if f[2] is not None and f[1] is not None
        ]
        return {
            "derivados": sum(1 for f in filas if desde <= f[1] < hasta),
            "revisados": len(resueltos),
            "aprobados": sum(1 for f in resueltos if f[0] == "aprobado"),
            "editados": sum(1 for f in resueltos if f[0] == "editado"),
            "rechazados": sum(1 for f in resueltos if f[0] == "rechazado"),
            "pendientes": len(pendientes_al_cierre),
            "mas_antiguo": min((f[1] for f in pendientes_al_cierre), default=None),
            "estudiantes_revisados": len(estudiantes_revisados),
            "estudiantes_revisados_ids": sorted(estudiantes_revisados),
            "sin_atribucion": sum(1 for f in resueltos if not f[3]),
            "horas": horas,
        }

    # ── 7 · Clases del alcance ──────────────────────────────────────────────

    def clases(self) -> list[dict]:
        """Una fila por clase, con su docente, su tamaño y su contexto curricular."""
        filas = self._ejecutar(
            """
            SELECT mat.clase,
                   MAX(c.creador) AS docente,
                   COUNT(DISTINCT mat.estudiante) AS matriculados,
                   COUNT(DISTINCT v.estudiante) AS activos,
                   MAX(COALESCE(c.unidad_curricular, '')) AS unidad,
                   MAX(c.contexto_actualizado_en) AS actualizado,
                   MAX(COALESCE(pd.facultad, '')) AS facultad_docente,
                   MAX(COALESCE(NULLIF(btrim(pd.nombre), ''), '')) AS nombre_docente
              FROM matriculas mat
              JOIN clase c ON c.id = mat.clase
              LEFT JOIN persona pd ON pd.sujeto_google = c.creador
              LEFT JOIN validos v
                ON v.estudiante = mat.estudiante AND v.clase = mat.clase
             GROUP BY mat.clase
            """
        )
        return [
            {
                "clase": f[0], "docente": f[1], "matriculados": int(f[2]),
                "activos": int(f[3]), "unidad": f[4] or "", "actualizado": f[5],
                "facultad_docente": f[6] or "", "nombre_docente": f[7] or "",
            }
            for f in filas
        ]

    # ── 8 · Versiones observadas ────────────────────────────────────────────

    def versiones(self, clases: list[str], periodo: tuple) -> list[dict]:
        """Qué corpus y qué modelo respondieron, según `evento_telemetria`.

        Sólo eventos de contexto educativo: `EQ-031` excluye el uso profesional
        de los agregados, y la columna está en la fila justamente para poder
        aplicarlo sin volver a preguntar por el rol de nadie.
        """
        if not clases:
            return []
        desde, hasta = periodo
        self._cur.execute(
            """
            SELECT COALESCE(version_corpus, ''), COALESCE(version_modelo, ''),
                   COUNT(*)
              FROM evento_telemetria
             WHERE tipo = 'turno.respondido'
               AND contexto_de_uso = 'aprendizaje_estudiante'
               AND clase = ANY(%s)
               AND ocurrido_en >= %s AND ocurrido_en < %s
             GROUP BY 1, 2
             ORDER BY COUNT(*) DESC, 1, 2
            """,
            (clases, desde, hasta),
        )
        return [
            {"corpus": f[0], "modelo": f[1], "turnos": int(f[2])}
            for f in self._cur.fetchall()
        ]

    def cobertura_por_corpus(self, clases: list[str], periodo: tuple) -> list[dict]:
        """Cobertura observada por versión de corpus, de la más reciente atrás.

        Sale de `evento_telemetria` y no de `historial_material` porque la
        versión de corpus **sólo** existe en el evento: el material recuperado
        no sabe bajo qué edición del corpus se recuperó. Por eso la cobertura de
        este indicador usa `procedencia` —lo que la respuesta declaró— y no la
        presencia de material, y su definición lo dice así en el catálogo.
        """
        if not clases:
            return []
        desde, hasta = periodo
        self._cur.execute(
            """
            SELECT version_corpus,
                   COUNT(*) AS turnos,
                   COUNT(*) FILTER (
                       WHERE COALESCE(metadatos->>'procedencia', '')
                             NOT IN ('', 'sin-fuente')
                   ) AS con_fuente,
                   MAX(ocurrido_en) AS ultimo
              FROM evento_telemetria
             WHERE tipo = 'turno.respondido'
               AND contexto_de_uso = 'aprendizaje_estudiante'
               AND COALESCE(version_corpus, '') <> ''
               AND clase = ANY(%s)
               AND ocurrido_en >= %s AND ocurrido_en < %s
             GROUP BY version_corpus
             ORDER BY MAX(ocurrido_en) DESC
            """,
            (clases, desde, hasta),
        )
        return [
            {
                "corpus": f[0], "turnos": int(f[1]),
                "con_fuente": int(f[2]), "ultimo": f[3],
            }
            for f in self._cur.fetchall()
        ]

    def apertura_de_fuentes(self) -> dict:
        """Respuestas con material cuyo panel de fuentes se abrió.

        Se cuenta cada turno una sola vez aunque la persona abra el panel más
        de una vez. El alcance sale de `validos`; el evento se correlaciona por
        sujeto y turno, por lo que una referencia de clase ausente no amplía la
        población y una referencia distinta tampoco cruza cursos.
        """
        filas = self._ejecutar(
            """
            SELECT COUNT(*) FILTER (WHERE v.con_material),
                   COUNT(*) FILTER (
                       WHERE v.con_material AND EXISTS (
                           SELECT 1
                             FROM evento_telemetria e
                            WHERE e.tipo = 'fuentes.abiertas'
                              AND e.contexto_de_uso = 'aprendizaje_estudiante'
                              AND e.identificador_sujeto = v.estudiante
                              AND e.turno = v.turno
                              AND (e.clase IS NULL OR e.clase = v.clase)
                              AND e.ocurrido_en >= %s AND e.ocurrido_en < %s
                       )
                   )
              FROM validos v
            """,
            list(self._periodo),
        )
        fila = filas[0] if filas else (0, 0)
        return {"elegibles": int(fila[0]), "abiertas": int(fila[1])}

    def autocorreccion(self) -> dict:
        """Candidatos detectados y confirmados explícitamente por turno.

        La confirmación se correlaciona con un candidato del mismo sujeto y
        turno. Un reintento no duplica por la clave idempotente de telemetría.
        """
        filas = self._ejecutar(
            """
            SELECT COUNT(*) FILTER (
                       WHERE EXISTS (
                           SELECT 1 FROM evento_telemetria e
                            WHERE e.tipo = 'autocorreccion.detectada'
                              AND e.contexto_de_uso = 'aprendizaje_estudiante'
                              AND e.identificador_sujeto = v.estudiante
                              AND e.turno = v.turno
                              AND (e.clase IS NULL OR e.clase = v.clase)
                              AND e.ocurrido_en >= %s AND e.ocurrido_en < %s
                       )
                   ),
                   COUNT(*) FILTER (
                       WHERE EXISTS (
                           SELECT 1 FROM evento_telemetria d
                            WHERE d.tipo = 'autocorreccion.detectada'
                              AND d.contexto_de_uso = 'aprendizaje_estudiante'
                              AND d.identificador_sujeto = v.estudiante
                              AND d.turno = v.turno
                              AND (d.clase IS NULL OR d.clase = v.clase)
                              AND d.ocurrido_en >= %s AND d.ocurrido_en < %s
                       ) AND EXISTS (
                           SELECT 1 FROM evento_telemetria c
                            WHERE c.tipo = 'autocorreccion.confirmada'
                              AND c.contexto_de_uso = 'aprendizaje_estudiante'
                              AND c.identificador_sujeto = v.estudiante
                              AND c.turno = v.turno
                              AND (c.clase IS NULL OR c.clase = v.clase)
                              AND c.ocurrido_en >= %s AND c.ocurrido_en < %s
                       )
                   )
              FROM validos v
            """,
            [*self._periodo, *self._periodo, *self._periodo],
        )
        fila = filas[0] if filas else (0, 0)
        return {"detectadas": int(fila[0]), "confirmadas": int(fila[1])}

    # ── 9 · Calidad de telemetría ──────────────────────────────────────────

    def calidad_de_telemetria(
        self,
        clases: list[str],
        estudiantes: list[str],
        periodo: tuple,
    ) -> dict:
        """Completitud y demora de los hechos atribuibles al alcance.

        Los eventos con clase se acotan directamente. Los que carecen de ella
        sólo se incluyen cuando su sujeto pertenece a la población autorizada;
        así la propia ausencia de clase continúa siendo observable sin abrir el
        alcance de un docente ni mezclar hechos institucionales sin atribución.
        """
        if not clases and not estudiantes:
            return {
                "eventos": 0, "sin_clase": 0, "sin_concepto": 0,
                "sin_turno": 0, "corpus_desconocido": 0,
                "modelo_desconocido": 0, "retrasados": 0,
                "retraso_p95_segundos": None, "tipos_observados": [],
                "duplicados": 0, "conflictos_idempotencia": 0,
                "eventos_incompatibles": 0, "cobertura_por_productor": [],
                "periodos_observacion_baja": [],
            }
        desde, hasta = periodo
        self._cur.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (
                       WHERE clase IS NULL AND tipo IN (
                           'turno.enviado', 'turno.respondido',
                           'supervision.derivada', 'supervision.decidida',
                           'curricular.actualizado', 'fuentes.abiertas',
                           'respuesta.copiada', 'grafica.generada',
                           'grafica.abierta', 'grafica.interaccion',
                           'grafica.rango_cambiado', 'grafica.exportada',
                           'supervision.abierta'
                       )
                   ),
                   COUNT(*) FILTER (
                       WHERE concepto IS NULL AND tipo IN (
                           'autocorreccion.detectada', 'autocorreccion.confirmada'
                       )
                   ),
                   COUNT(*) FILTER (
                       WHERE turno IS NULL AND tipo IN (
                           'turno.enviado', 'turno.respondido',
                           'supervision.derivada', 'supervision.decidida',
                           'fuentes.abiertas', 'respuesta.copiada',
                           'grafica.generada', 'grafica.abierta',
                           'grafica.interaccion', 'grafica.rango_cambiado',
                           'grafica.exportada', 'supervision.abierta',
                           'autocorreccion.detectada', 'autocorreccion.confirmada'
                       )
                   ),
                   COUNT(*) FILTER (
                       WHERE tipo = 'turno.respondido'
                         AND COALESCE(version_corpus, '') = ''
                   ),
                   COUNT(*) FILTER (
                       WHERE tipo = 'turno.respondido'
                         AND COALESCE(version_modelo, '') = ''
                   ),
                   COUNT(*) FILTER (
                       WHERE registrado_en - ocurrido_en > interval '1 hour'
                   ),
                   percentile_cont(0.95) WITHIN GROUP (
                       ORDER BY GREATEST(
                           EXTRACT(EPOCH FROM registrado_en - ocurrido_en), 0
                       )
                   ),
                   ARRAY_AGG(DISTINCT tipo ORDER BY tipo)
                   , COUNT(*) FILTER (
                       WHERE (tipo LIKE 'grafica.%%' AND NOT (metadatos ? 'grafica'))
                          OR (tipo = 'grafica.exportada'
                              AND (NOT (metadatos ? 'formato') OR NOT (metadatos ? 'tema')))
                          OR (tipo = 'supervision.decidida' AND NOT (metadatos ? 'decision'))
                          OR (tipo = 'fuentes.abiertas' AND NOT (metadatos ? 'materiales'))
                          OR (origen = 'backend' AND tipo IN (
                              'fuentes.abiertas', 'respuesta.copiada', 'grafica.generada',
                              'grafica.abierta', 'grafica.interaccion',
                              'grafica.rango_cambiado', 'grafica.exportada',
                              'supervision.abierta', 'informe.generado',
                              'informe.descargado', 'autocorreccion.detectada',
                              'autocorreccion.confirmada'
                          ))
                          OR (origen = 'interfaz' AND tipo IN (
                              'turno.enviado', 'turno.respondido',
                              'supervision.derivada', 'supervision.decidida',
                              'curricular.actualizado'
                          ))
                   )
              FROM evento_telemetria
             WHERE (
                    clase = ANY(%s)
                    OR (clase IS NULL AND identificador_sujeto = ANY(%s))
                   )
               AND ocurrido_en >= %s AND ocurrido_en < %s
               AND contexto_de_uso = 'aprendizaje_estudiante'
            """,
            (clases, estudiantes, desde, hasta),
        )
        fila = self._cur.fetchone()
        calidad = {
            "eventos": int(fila[0]),
            "sin_clase": int(fila[1]),
            "sin_concepto": int(fila[2]),
            "sin_turno": int(fila[3]),
            "corpus_desconocido": int(fila[4]),
            "modelo_desconocido": int(fila[5]),
            "retrasados": int(fila[6]),
            "retraso_p95_segundos": float(fila[7]) if fila[7] is not None else None,
            "tipos_observados": list(fila[8] or []),
            "eventos_incompatibles": int(fila[9]),
        }

        self._cur.execute(
            """
            SELECT categoria, COUNT(*)
              FROM incidencia_telemetria
             WHERE (clase = ANY(%s) OR identificador_sujeto = ANY(%s))
               AND registrado_en >= %s AND registrado_en < %s
             GROUP BY categoria
            """,
            (clases, estudiantes, desde, hasta),
        )
        incidencias = {categoria: int(cantidad) for categoria, cantidad in self._cur.fetchall()}
        calidad["duplicados"] = incidencias.get("duplicado", 0)
        calidad["conflictos_idempotencia"] = incidencias.get(
            "conflicto_idempotencia", 0
        )
        calidad["eventos_incompatibles"] += incidencias.get("incompatible", 0)

        self._cur.execute(
            """
            SELECT tipo, origen, COUNT(*)
              FROM evento_telemetria
             WHERE (clase = ANY(%s)
                    OR (clase IS NULL AND identificador_sujeto = ANY(%s)))
               AND ocurrido_en >= %s AND ocurrido_en < %s
               AND contexto_de_uso = 'aprendizaje_estudiante'
             GROUP BY tipo, origen
            """,
            (clases, estudiantes, desde, hasta),
        )
        observados = {
            (tipo, origen): int(cantidad)
            for tipo, origen, cantidad in self._cur.fetchall()
        }
        calidad["cobertura_por_productor"] = [
            {
                "tipo": tipo.value,
                "productor": ORIGEN_DE[tipo].value,
                "eventos": observados.get((tipo.value, ORIGEN_DE[tipo].value), 0),
                "observado": observados.get((tipo.value, ORIGEN_DE[tipo].value), 0) > 0,
            }
            for tipo in TipoDeEvento
        ]

        self._cur.execute(
            f"""
            SELECT (ocurrido_en AT TIME ZONE '{ZONA_HORARIA}')::date, COUNT(*)
              FROM evento_telemetria
             WHERE (clase = ANY(%s)
                    OR (clase IS NULL AND identificador_sujeto = ANY(%s)))
               AND ocurrido_en >= %s AND ocurrido_en < %s
               AND contexto_de_uso = 'aprendizaje_estudiante'
             GROUP BY 1
               HAVING COUNT(*) < %s
             ORDER BY 1
            """,
            (clases, estudiantes, desde, hasta, MUESTRA_MINIMA),
        )
        calidad["periodos_observacion_baja"] = [
            {"fecha": fecha.isoformat(), "eventos": int(cantidad)}
            for fecha, cantidad in self._cur.fetchall()
        ]
        return calidad

    # ── 10 · Completitud de perfiles docentes ───────────────────────────────

    def docentes(self) -> dict:
        """Cuántos docentes del alcance tienen nombre y facultad declarados."""
        filas = self._ejecutar(
            """
            SELECT DISTINCT c.creador,
                   COALESCE(NULLIF(btrim(p.nombre), ''), '') AS nombre,
                   COALESCE(p.facultad, '') AS facultad
              FROM matriculas mat
              JOIN clase c ON c.id = mat.clase
              LEFT JOIN persona p ON p.sujeto_google = c.creador
            """
        )
        return {
            "total": len(filas),
            "completos": sum(1 for f in filas if f[1] and f[2]),
        }
