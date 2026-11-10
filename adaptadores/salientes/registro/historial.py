from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.conexion import conectar
from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import traducir_fallo

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dominio.puertos.registro import EntradaDeTurno

MENSAJE_TITULABLE_SQL = """(array_agg(contenido ORDER BY
    CASE WHEN lower(contenido) ~ 'deriv|l[ií]mit|integral|[=^$]' THEN 0 ELSE 1 END, id)
    FILTER (WHERE autor = 'estudiante' AND btrim(contenido) <> ''
      AND lower(btrim(contenido)) !~ '^(hola|buenos días|buenas tardes|buenas noches|gracias|muchas gracias|ok|vale|sí|si|no)[[:space:]!¿¡?.,;]*$'))[1]"""

class AdaptadorHistorialPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _transaccion(self) -> Iterator[Any]:
        with traducir_fallo(), conectar(self._cadena) as cnx, cnx.transaction():
            yield cnx

    def abrir_estado_operativo(self, sujeto, conversacion):
        from adaptadores.salientes.registro.estado_conversacional import CheckpointConversacion

        return CheckpointConversacion(self._cadena, sujeto, conversacion)

    def registrar_turno(self, entrada: EntradaDeTurno) -> None:
        fallos = entrada.validar()
        if fallos:
            raise ValueError("entrada de turno no admisible: " + "; ".join(fallos))

        with conectar(self._cadena) as cnx, cnx.cursor() as cur:

            cur.execute(
                """
                INSERT INTO historial_turno (
                    turno, identificador_sesion, identificador_sujeto,
                    momento, autor, contenido, degradado,
                    nivel, procedencia_origen, procedencia_referencia,
                    consentimiento_evento, contexto_de_uso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    entrada.turno,
                    entrada.identificador_sesion,
                    entrada.identificador_sujeto,
                    entrada.momento,
                    entrada.autor,
                    entrada.contenido,
                    entrada.degradado,
                    entrada.nivel,
                    entrada.procedencia_origen,
                    entrada.procedencia_referencia,

                    entrada.consentimiento_evento,

                    str(entrada.contexto_de_uso),
                ),
            )
            (mensaje,) = cur.fetchone()

            if entrada.bloques:
                cur.executemany(
                    """
                    INSERT INTO historial_bloque (
                        historial, orden, tipo, contenido, sello, alternativo
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (mensaje, orden, b.tipo, b.contenido, b.sello, b.alternativo or None)
                        for orden, b in enumerate(entrada.bloques)
                    ],
                )
            if entrada.citas:
                cur.executemany(
                    """
                    INSERT INTO historial_cita (historial, marca, expresion)
                    VALUES (%s, %s, %s)
                    """,
                    [(mensaje, c.marca, c.expresion) for c in entrada.citas],
                )
            if entrada.material:

                cur.executemany(
                    """
                    INSERT INTO historial_material (
                        historial, orden, fragmento, obra, relacion, similitud
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (mensaje, m.orden, m.fragmento, m.obra, m.relacion, m.similitud)
                        for m in entrada.material
                    ],
                )
            if entrada.conceptos:
                cur.executemany(
                    """
                    INSERT INTO historial_concepto (historial, orden, concepto)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (mensaje, orden, concepto)
                        for orden, concepto in enumerate(entrada.conceptos)
                    ],
                )
            cnx.commit()

    _CLAVES_DE_BORRADO = ("identificador_sesion",)

    def _borrar_del_sujeto(self, identificador_sujeto: str, columna: str = "", valor: str = "") -> int:
        condiciones = ["identificador_sujeto = %s"]
        parametros = [identificador_sujeto]
        if columna:
            if columna not in self._CLAVES_DE_BORRADO:
                raise ValueError(f"columna de borrado no permitida: «{columna}»")
            condiciones.append(f"{columna} = %s")
            parametros.append(valor)

        with conectar(self._cadena) as cnx, cnx.cursor() as cur:
            cur.execute(
                "DELETE FROM historial_turno WHERE " + " AND ".join(condiciones),
                tuple(parametros),
            )
            borradas = cur.rowcount
            cur.execute(
                "DELETE FROM tutor_estado_conversacion WHERE sujeto=%s" +
                (" AND conversacion=%s" if columna == "identificador_sesion" else ""),
                (identificador_sujeto, valor) if columna == "identificador_sesion" else (identificador_sujeto,),
            )
            cnx.commit()
        return borradas

    def suprimir_sesion(self, identificador_sesion: str, identificador_sujeto: str) -> int:
        return self._borrar_del_sujeto(
            identificador_sujeto, "identificador_sesion", identificador_sesion
        )

    def suprimir_sujeto(self, identificador_sujeto: str) -> int:
        return self._borrar_del_sujeto(identificador_sujeto)

    def historial_de(self, identificador_sujeto: str) -> list[dict]:
        with self._transaccion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"""
                SELECT identificador_sesion,
                       min(momento)          AS inicio,
                       max(momento)          AS ultimo,
                       count(DISTINCT turno) AS turnos,
                       (array_agg(contenido ORDER BY id)
                          FILTER (WHERE autor = 'estudiante'))[1] AS primer_mensaje,
                       {MENSAJE_TITULABLE_SQL} AS mensaje_para_titulo
                  FROM historial_turno
                 WHERE identificador_sujeto = %s
              GROUP BY identificador_sesion
              ORDER BY max(momento) DESC
                """,
                (identificador_sujeto,),
            )
            filas = cur.fetchall()
        return [
            {
                "sesion": fila[0],
                "inicio": fila[1],
                "ultimo": fila[2],
                "turnos": fila[3],
                "primer_mensaje": fila[4] or "",
                "mensaje_para_titulo": fila[5] or fila[4] or "",
            }
            for fila in filas
        ]

    def hilo_de(
        self,
        identificador_sesion: str,
        identificador_sujeto: str,
        *,
        actor: str = "",
        operacion: str = "conversacion.consultada",
    ) -> list[dict]:

        with self._transaccion() as cnx, cnx.cursor() as cur:
            if actor:
                anotar(
                    cur,
                    operacion,
                    actor=actor,
                    sujeto_afectado=identificador_sujeto,

                    detalle={"conversacion": identificador_sesion},
                )
            return self._hilo_de_cursor(
                cur, "h.identificador_sesion = %s AND h.identificador_sujeto = %s",
                (identificador_sesion, identificador_sujeto),
            )

    def _hilo_de_cursor(self, cur, condicion, valores):
        cur.execute(
            f"""
            SELECT id, turno, momento, autor, contenido, degradado,
                   nivel, procedencia_origen, procedencia_referencia
              FROM historial_turno h
             WHERE {condicion}
          ORDER BY id
            """,
            valores,
        )
        filas = cur.fetchall()
        if not filas:
            return []

        mensajes = [f[0] for f in filas]
        cur.execute(
            """
            SELECT historial, tipo, contenido, sello, alternativo
              FROM historial_bloque
             WHERE historial = ANY(%s)
          ORDER BY historial, orden
            """,
            (mensajes,),
        )
        bloques: dict[int, list[dict]] = {}
        for h, tipo, contenido, sello, alternativo in cur.fetchall():
            bloques.setdefault(h, []).append(
                {
                    "tipo": tipo,
                    "contenido": contenido,
                    "sello": sello,
                    "alternativo": alternativo or "",
                }
            )
        cur.execute(
            """
            SELECT historial, marca, expresion
              FROM historial_cita
             WHERE historial = ANY(%s)
          ORDER BY historial, marca
            """,
            (mensajes,),
        )
        citas: dict[int, list[dict]] = {}
        for h, marca, expresion in cur.fetchall():
            citas.setdefault(h, []).append({"marca": marca, "expresion": expresion})

        material = _material_de(cur, mensajes)

        return [
            {
                "turno": fila[1],
                "momento": fila[2],
                "autor": fila[3],
                "contenido": fila[4],
                "degradado": fila[5],
                "nivel": fila[6],
                "procedencia": {"origen": fila[7], "referencia": fila[8]},
                "bloques": bloques.get(fila[0], []),
                "citas": citas.get(fila[0], []),

                "material": material.get(fila[0], []),
            }
            for fila in filas
        ]

def _material_de(cur, mensajes: list[int]) -> dict[int, list[dict]]:
    cur.execute("SELECT to_regclass('public.historial_material')")
    (existe,) = cur.fetchone()
    if existe is None:
        return {}

    cur.execute(
        """
        SELECT historial, fragmento, obra, relacion, similitud
          FROM historial_material
         WHERE historial = ANY(%s)
      ORDER BY historial, orden
        """,
        (mensajes,),
    )
    material: dict[int, list[dict]] = {}
    for h, fragmento, obra, relacion, similitud in cur.fetchall():
        material.setdefault(h, []).append(
            {
                "fragmento": fragmento,
                "obra": obra,
                "relacion": relacion,
                "similitud": float(similitud) if similitud is not None else None,
            }
        )
    return material
