"""Lecturas privadas por turno y versión; sin invocar al proveedor al leer KPI."""

import hashlib
import json

from adaptadores.salientes.conexion import conectar
from adaptadores.salientes.registro.estado_vigente_db import AdaptadorEstadoVigentePostgres
from dominio.modelo.acceso import calcular_acceso, permite_escritura_longitudinal
from dominio.modelo.factores_conductuales import VERSION
from dominio.modelo.fenomenos_anteproyecto import _metadatos
from dominio.modelo.fusion_conductual import lectura_guardada

FILTROS_MATEMATICOS = {"verificación del intento del estudiante", "verificación simbólica"}


def habilitado(cur, sujeto):
    cur.execute(
        "SELECT edad_declarada, es_cuenta_prueba FROM persona WHERE sujeto_google = %s FOR SHARE",
        (sujeto,),
    )
    fila = cur.fetchone()
    if not fila or fila[0] is None or fila[0] < 18 or fila[1]:
        return False
    estado = AdaptadorEstadoVigentePostgres("").desde_cursor(cur, sujeto)
    return estado is not None and permite_escritura_longitudinal(calcular_acceso(estado))


def guardar(cur, historial, mensaje, lectura, trazas, *, origen, huella):  # noqa: PLR0913 — contrato de evidencia explícito
    if not lectura_guardada(lectura, mensaje):
        return False
    cur.execute(
        """INSERT INTO analisis_conductual
           (historial, version, modelo, huella, origen, lectura, trazas_matematicas)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
           ON CONFLICT (historial, version) DO NOTHING RETURNING historial""",
        (
            historial,
            VERSION,
            lectura.get("modelo", ""),
            huella,
            origen,
            json.dumps(lectura, ensure_ascii=False),
            json.dumps(
                [t for t in trazas if t.get("filtro") in FILTROS_MATEMATICOS], ensure_ascii=False
            ),
        ),
    )
    return cur.fetchone() is not None


class AdaptadorFactoresPostgres:
    def __init__(self, cadena):
        self.cadena = cadena

    def registrar(self, ctx):
        if not ctx.identificador_sujeto or ctx.contexto_de_uso != "aprendizaje_estudiante":
            return False
        trazas = [{"filtro": t.filtro, "metadatos": t.metadatos} for t in ctx.trazas]
        lectura = _metadatos(trazas, "interpretación semántica experimental").get(
            "analisis_conductual", {}
        )
        if not lectura_guardada(lectura, ctx.texto_estudiante):
            return False
        with conectar(self.cadena) as cnx, cnx.cursor() as cur:
            if not habilitado(cur, ctx.identificador_sujeto):
                return False
            cur.execute(
                """SELECT h.id FROM historial_turno h
                   WHERE h.turno=%s AND h.identificador_sesion=%s AND h.identificador_sujeto=%s
                     AND h.autor='estudiante' AND h.contexto_de_uso='aprendizaje_estudiante'
                     AND EXISTS (SELECT 1 FROM historial_turno s WHERE s.turno=h.turno
                         AND s.identificador_sesion=h.identificador_sesion
                         AND s.identificador_sujeto=h.identificador_sujeto AND s.autor='sistema'
                         AND NOT s.degradado AND s.contexto_de_uso='aprendizaje_estudiante')
                   ORDER BY h.id LIMIT 1""",
                (ctx.identificador_turno, ctx.identificador_sesion, ctx.identificador_sujeto),
            )
            fila = cur.fetchone()
            if not fila:
                return False
            huella = hashlib.sha256(
                json.dumps(
                    {
                        "mensaje": ctx.texto_estudiante,
                        "historial": ctx.historial_reciente[-3:],
                        "version": VERSION,
                    },
                    sort_keys=True,
                    default=str,
                ).encode()
            ).hexdigest()
            return guardar(
                cur, fila[0], ctx.texto_estudiante, lectura, trazas, origen="turno", huella=huella
            )
