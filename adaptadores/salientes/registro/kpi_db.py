from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import (
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres
from adaptadores.salientes.registro.estado_vigente_db import AdaptadorEstadoVigentePostgres
from adaptadores.salientes.registro.kpi_armado import ArmadoKPI
from adaptadores.salientes.registro.kpi_consultas import ConsultasKPI, alcance_sql
from adaptadores.salientes.registro.lectura_factores import completar_trazas
from adaptadores.salientes.registro.lectura_trazas_anteproyecto import leer_trazas
from dominio.kpi.contratos import VERSION_CATALOGO, Alcance, ContextoDeCalculo
from dominio.kpi.definiciones import VERSION_DEFINICIONES
from dominio.modelo.acceso import calcular_acceso, permite_escritura_longitudinal
from dominio.modelo.factores_agregados import resumir_factores
from dominio.modelo.fenomenos_anteproyecto import resumir_trazas
from dominio.modelo.identidad import MAYORIA_DE_EDAD
from dominio.modelo.indicios_observables import resumir_lenguaje
from dominio.modelo.observables_dialogo import resumir_observables
from dominio.modelo.telemetria import TipoDeEvento
from dominio.puertos.almacen import EscrituraRechazada

if TYPE_CHECKING:
    from dominio.kpi.consulta import ConsultaKPI

OPERACION_KPI = "consultar_kpi_institucional"


class AdaptadorKPIPostgres(RepositorioPostgres):

    def calcular(self, consulta: ConsultaKPI) -> dict:
        institucional = consulta.alcance is Alcance.INSTITUCIONAL
        condicion, parametros = alcance_sql(
            consulta.clase,
            None if institucional else consulta.actor,
            consulta.filtros,
        )
        periodo = (consulta.periodo.desde, consulta.periodo.hasta)
        corte_secuencia = None
        corte_instante = None

        with self._conexion() as cnx, cnx.cursor() as cur:
            if institucional:
                exigir_investigador_administrador(cur, consulta.actor)

                corte_secuencia, corte_instante = anotar(
                    cur,
                    OPERACION_KPI,
                    actor=consulta.actor,
                    detalle={
                        "catalogo": VERSION_CATALOGO,
                        "desde": consulta.periodo.desde.isoformat(),
                        "hasta": consulta.periodo.hasta.isoformat(),
                        "filtros": consulta.filtros_declarados,
                        "codigos": list(consulta.codigos),
                        "incluye_texto": False,
                    },
                )
            else:

                cur.execute(
                    "SELECT 1 FROM clase WHERE id = %s AND creador = %s "
                    "AND archivada_en IS NULL FOR SHARE",
                    (consulta.clase, consulta.actor),
                )
                if cur.fetchone() is None:
                    raise EscrituraRechazada("la clase no pertenece al docente")
            crudo = self._materia_prima(
                cur, condicion, parametros, periodo, consulta.filtros
            )
            cnx.commit()

        versiones_corpus = tuple(sorted({
            fila["corpus"] for fila in crudo["versiones"] if fila["corpus"]
        }))
        versiones_modelo = tuple(sorted({
            fila["modelo"] for fila in crudo["versiones"] if fila["modelo"]
        }))
        contexto = ContextoDeCalculo(
            periodo=consulta.periodo,
            calculado_en=corte_instante or datetime.now(UTC),
            filtros=consulta.filtros_declarados,
            version_corpus=versiones_corpus[0] if len(versiones_corpus) == 1 else "",
            version_modelo=versiones_modelo[0] if len(versiones_modelo) == 1 else "",
            versiones_corpus=versiones_corpus,
            versiones_modelo=versiones_modelo,
        )
        resultados = ArmadoKPI(contexto, crudo).armar(consulta.alcance, consulta.codigos)
        return {
            "version_catalogo": VERSION_CATALOGO,
            "version_definiciones": VERSION_DEFINICIONES,
            "alcance": consulta.alcance.value,
            "corte": {
                "instante": corte_instante.isoformat() if corte_instante else contexto.calculado_en.isoformat(),
                "secuencia": corte_secuencia,
            },
            "periodo": consulta.periodo.como_json(),
            "filtros": consulta.filtros_declarados,
            "poblacion": {
                "estudiantes_elegibles": len(crudo["estudiantes"]),
                "clases": len(crudo["clases"]),
            },
            "versiones_observadas": {
                "corpus": list(versiones_corpus),
                "modelos": list(versiones_modelo),
            },
            "calidad": _resumir_calidad(crudo, resultados),
            "indicadores": [resultado.como_json() for resultado in resultados],
        }

    @staticmethod
    def _materia_prima(
        cur: Any, condicion: str, parametros: list, periodo: tuple, filtros: dict
    ) -> dict:

        consultas = ConsultasKPI(cur, condicion, parametros, periodo, filtros)
        clases = consultas.clases()
        identificadores = [c["clase"] for c in clases]
        estudiantes = consultas.actividad_por_estudiante()
        sujetos = [fila["estudiante"] for fila in estudiantes]
        vigencia = AdaptadorEstadoVigentePostgres("")
        habilitados = set()
        for fila in estudiantes:
            if fila["edad"] is None or fila["edad"] < MAYORIA_DE_EDAD:
                continue
            estado = vigencia.desde_cursor(cur, fila["estudiante"])
            if estado is not None and permite_escritura_longitudinal(calcular_acceso(estado)):
                habilitados.add(fila["estudiante"])
        textos = [texto for estudiante, texto in consultas.textos_indicios()
                  if estudiante in habilitados]
        referencias = [fila for fila in consultas.trazas_anteproyecto()
                       if fila["estudiante"] in habilitados]
        registros, faltantes_traza = leer_trazas(referencias)
        resumen_trazas = resumir_trazas(registros)
        mensajes = [m for m in consultas.mensajes_observables() if m["estudiante"] in habilitados]
        observables = resumir_observables(mensajes, registros, *periodo, faltantes_traza)
        indicios = resumir_lenguaje(textos)
        ansiedad = next(c for c in indicios["componentes"] if c["clave_origen"] == "PS-Anx")
        factores = completar_trazas([r for r in consultas.factores_hibridos() if r["estudiante"] in habilitados])
        return {
            "estudiantes": estudiantes,
            "factores_hibridos": resumir_factores(factores, desde=periodo[0], hasta=periodo[1]),
            "observables_dialogo": observables,
            "fenomenos_anteproyecto": {
                "ansiedad": (ansiedad["numerador"], ansiedad["denominador"]),
                "concepciones": (resumen_trazas["concepciones_detectadas"], resumen_trazas["clasificados"]),
                "reiteracion": (resumen_trazas["reincidencias"], resumen_trazas["oportunidades_tras_correccion"]),
                "trazas_faltantes": faltantes_traza,
                "por_concepcion": resumen_trazas["por_concepcion"],
                "cobertura": resumen_trazas,
            },
            "cobertura_instrumentos": {
                "mensajes_analizables_ps_anx": ansiedad["denominador"],
                "trazas_referenciadas": len(referencias),
                "trazas_legibles": resumen_trazas["trazas_legibles"],
                "trazas_faltantes": faltantes_traza,
                "sondeos_ofrecidos": resumen_trazas["sondeos_ofrecidos"],
                "sondeos_clasificados": resumen_trazas["clasificados"],
                "intentos_verificables": resumen_trazas["intentos_verificables"],
                "correcciones_candidatas": resumen_trazas["correcciones_candidatas"],
                "reintentos_observados": resumen_trazas["oportunidades_tras_correccion"],
            },
            "conversaciones": consultas.conversaciones(),
            "recuperacion": consultas.recuperacion(),
            "material": consultas.material(),
            "bloques": consultas.bloques(),
            "niveles": consultas.niveles(),
            "supervision": consultas.supervision(identificadores, periodo),
            "clases": clases,
            "docentes": consultas.docentes(),
            "versiones": consultas.versiones(identificadores, periodo),
            "cobertura_por_corpus": consultas.cobertura_por_corpus(identificadores, periodo),
            "apertura_de_fuentes": consultas.apertura_de_fuentes(),
            "autocorreccion": consultas.autocorreccion(),
            "continuacion": consultas.continuacion(),
            "sin_retorno_7d": consultas.sin_retorno_7d(),
            "referencias_conceptuales": consultas.referencias_conceptuales(),
            "calidad_telemetria": consultas.calidad_de_telemetria(
                identificadores, sujetos, periodo
            ),
        }

def _resumir_calidad(crudo: dict, resultados: list) -> dict:
    estudiantes = crudo["estudiantes"]
    faltantes = {
        "edad": sum(1 for fila in estudiantes if fila["edad"] is None),
        "facultad": sum(1 for fila in estudiantes if not fila["facultad"]),
        "programa": sum(1 for fila in estudiantes if not fila["programa"]),
        "semestre": sum(1 for fila in estudiantes if fila["semestre"] is None),
    }
    completos = sum(
        1 for fila in estudiantes
        if fila["edad"] is not None and fila["facultad"]
        and fila["programa"] and fila["semestre"] is not None
    )
    por_estado: dict[str, int] = {}
    for resultado in resultados:
        estado = resultado.estado.value
        por_estado[estado] = por_estado.get(estado, 0) + 1
    telemetria = crudo["calidad_telemetria"]
    return {
        "perfiles": {
            "total_estudiantes": len(estudiantes),
            "completos": completos,
            "incompletos": len(estudiantes) - completos,
            "faltantes_por_campo": faltantes,
            "docentes": crudo["docentes"],
        },
        "telemetria": {
            **telemetria,
            "tipos_definidos": len(TipoDeEvento),
        },
        "instrumentos_prototipo": crudo["cobertura_instrumentos"],
        "metricas": {
            "total": len(resultados),
            "por_estado": por_estado,
            "no_calculables": sum(
                cantidad for estado, cantidad in por_estado.items()
                if estado != "disponible"
            ),
        },
        "reglas": {
            "muestra_minima_por_indicador": True,
            "sin_division_por_cero": True,
            "sin_ceros_para_ausencias": True,
            "zona_horaria": "America/Bogota",
            "supresion": {
                "tramite_abierto_bloquea_consulta_del_actor": True,
                "filas_personales_se_eliminan_por_sujeto": True,
                "supresion_de_celdas_por_tamano": False,
                "motivo_sin_supresion_de_celdas": (
                    "no existe una política institucional aprobada; los umbrales 5 y 10 "
                    "son reglas metodológicas de publicación, no anonimato"
                ),
            },
        },
    }
