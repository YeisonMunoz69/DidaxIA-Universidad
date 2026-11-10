"""
kpi_db.py — El cálculo del catálogo KPI v1.1, autorizado y auditado
=====================================================================

Orquesta las nueve lecturas de `kpi_consultas.py`, las pasa por
`kpi_armado.py` y devuelve resultados del catálogo. Lo que decide **aquí** y no
en la ruta son las dos cosas que no se pueden delegar al borde.

La autorización vive dentro de la transacción
--------------------------------------------------------
Para el docente, la propiedad de la clase se comprueba y retiene con `FOR
SHARE`; una clase ajena se rechaza. Además, cada lectura conserva la condición
`c.creador = %s` de `alcance_sql()`: el chequeo explícito da una negativa clara
y la consulta acotada mantiene la defensa en profundidad dentro de la misma
transacción.

Para el investigador, `exigir_investigador_administrador()` lee y **retiene** su
asignación con `FOR SHARE` hasta el commit. Una revocación concurrente no puede
confirmarse mientras la lectura ocurre.

La auditoría se escribe ANTES de leer
------------------------------------------------
`auditoria_sql.py` lo explica: para una lectura hay que anotar antes del
`SELECT`, de modo que un fallo de auditoría impida devolver lo leído. Al revés,
los agregados ya habrían salido y el registro faltaría. Las dos van en la misma
transacción, así que o quedan las dos o no queda ninguna (`EQ-023`).

⚠️ **Sólo se audita la lectura institucional.** Un docente consultando su propia
clase hace su trabajo ordinario, y anotar cada carga del panel llenaría
`auditoria_operacion` —la tabla que más sobrevive— con el uso normal del
producto. Lo que `EQ-023` manda auditar es el acceso institucional a datos de
personas que no son las suyas, y eso es exactamente lo que se anota.

Qué NO hace este adaptador
-----------------------------------
No construye rankings. No hay ningún `ORDER BY` sobre docentes ni ninguna
consulta que los ordene por cifra: el encargo lo prohíbe y la ausencia es la
forma de cumplirlo. `institucion.estudiantes_activos_por_clase` publica una
distribución justamente para no publicar un orden.


"""

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

if TYPE_CHECKING:  # pragma: no cover
    from dominio.kpi.consulta import ConsultaKPI

#: Con qué nombre queda registrada una lectura institucional de indicadores.
#: Constante por el mismo motivo que en `inventario_db.py` y `historial.py`: una
#: consulta de auditoría que buscara otra redacción no encontraría nada.
OPERACION_KPI = "consultar_kpi_institucional"


class AdaptadorKPIPostgres(RepositorioPostgres):
    """`PuertoCalculoKPI` sobre PostgreSQL."""

    def calcular(self, consulta: ConsultaKPI) -> dict:
        """Los indicadores del alcance, con su periodo, filtros y metodología.

        Devuelve un diccionario ya serializable: la ruta no vuelve a recorrer
        los resultados, de modo que no pueda añadir ni quitar campos al pasar.
        """
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
                # ⚠️ Antes de leer. Ver la cabecera.
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
                # Una clase ajena se niega de forma explícita. Mantener además
                # ``c.creador = actor`` dentro de cada lectura conserva la
                # defensa en profundidad si este chequeo cambia algún día.
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
        """Las nueve lecturas, en una sola transacción.

        `clases` se resuelve primero porque tres de las demás —cola, versiones y
        cobertura por corpus— se acotan por clase y no por estudiante: un
        elemento de la cola anterior a la migración 19 no tiene estudiante
        atribuido pero sí clase, y buscarlo por estudiante lo dejaría fuera sin
        que nadie lo notara.
        """
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
    """La superficie de calidad, derivada de la misma lectura de los KPI."""
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
