from __future__ import annotations

import statistics
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from dominio.kpi import catalogo as cat
from dominio.kpi import medidas
from dominio.kpi.contratos import Alcance, ContextoDeCalculo, ResultadoKPI
from dominio.modelo.factores_agregados import calcular_factores
from dominio.modelo.fenomenos_anteproyecto import detalle_cobertura
from dominio.modelo.observables_dialogo import calcular_observables

if TYPE_CHECKING:
    from datetime import datetime

def _percentil(valores: list[float], fraccion: float) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return float(ordenados[0])
    posicion = fraccion * (len(ordenados) - 1)
    bajo = int(posicion)
    alto = min(bajo + 1, len(ordenados) - 1)
    peso = posicion - bajo
    return float(ordenados[bajo] * (1 - peso) + ordenados[alto] * peso)

def _distribucion(valores: list[float]) -> tuple[float | None, dict]:
    if not valores:
        return None, {"observaciones": 0}
    return statistics.median(valores), {
        "observaciones": len(valores),
        "p25": _percentil(valores, 0.25),
        "p75": _percentil(valores, 0.75),
        "p95": _percentil(valores, 0.95),
        "minimo": float(min(valores)),
        "maximo": float(max(valores)),
    }

def _intervalos_entre_sesiones(conversaciones: list[dict]) -> list[float]:
    por_estudiante: dict[str, list[dict]] = {}
    for conversacion in conversaciones:
        por_estudiante.setdefault(conversacion["estudiante"], []).append(conversacion)
    intervalos: list[float] = []
    for sesiones in por_estudiante.values():
        ordenadas = sorted(sesiones, key=lambda s: s["inicio"])
        for anterior, siguiente in zip(ordenadas, ordenadas[1:], strict=False):
            delta = siguiente["inicio"] - anterior["fin"]
            if isinstance(delta, timedelta) and delta.total_seconds() >= 0:
                intervalos.append(delta.total_seconds() / 3600)
    return intervalos

class ArmadoKPI:

    def __init__(self, contexto: ContextoDeCalculo, crudo: dict) -> None:
        self._contexto = contexto
        self._crudo = crudo

    def _proporcion(self, codigo: str, partes: tuple[float, float], faltantes: int = 0):
        return medidas.proporcion(cat.buscar(codigo), self._contexto, partes, faltantes)

    def _conteo(self, codigo: str, valor: int, poblacion: int, detalle: dict | None = None):
        return medidas.conteo(cat.buscar(codigo), self._contexto, valor, poblacion, detalle)

    def _distribucion(self, codigo: str, valores: list[float]):
        mediana, percentiles = _distribucion(valores)
        return medidas.distribucion(cat.buscar(codigo), self._contexto, mediana, percentiles)

    def _adopcion(self) -> dict[str, ResultadoKPI]:
        estudiantes: list[dict] = self._crudo["estudiantes"]
        desde: datetime = self._contexto.periodo.desde
        hasta: datetime = self._contexto.periodo.hasta
        elegibles = len(estudiantes)
        activos = [e for e in estudiantes if e["turnos"]]

        semana = [
            e for e in activos if e["ultima"] is not None and e["ultima"] >= hasta - timedelta(days=7)
        ]

        con_ventana_7 = [
            e for e in activos
            if e["primera"] is not None
            and desde <= e["primera"] <= hasta - timedelta(days=7)
        ]
        con_ventana_30 = [
            e for e in activos
            if e["primera"] is not None
            and desde <= e["primera"] <= hasta - timedelta(days=30)
        ]
        return {
            "adopcion.activacion": self._proporcion(
                "adopcion.activacion", (len(activos), elegibles)
            ),
            "adopcion.actividad_semanal": self._proporcion(
                "adopcion.actividad_semanal", (len(semana), elegibles)
            ),
            "adopcion.retorno_7d": self._proporcion(
                "adopcion.retorno_7d",
                (sum(1 for e in con_ventana_7 if e["regreso_7"]), len(con_ventana_7)),
            ),
            "adopcion.retorno_30d": self._proporcion(
                "adopcion.retorno_30d",
                (sum(1 for e in con_ventana_30 if e["regreso_30"]), len(con_ventana_30)),
            ),
            "adopcion.dias_activos_por_estudiante": self._distribucion(
                "adopcion.dias_activos_por_estudiante", [float(e["dias"]) for e in activos]
            ),
            "adopcion.profundidad_conversacion": self._distribucion(
                "adopcion.profundidad_conversacion",
                [float(c["turnos"]) for c in self._crudo["conversaciones"]],
            ),
            "adopcion.intervalo_entre_sesiones": self._distribucion(
                "adopcion.intervalo_entre_sesiones",
                _intervalos_entre_sesiones(self._crudo["conversaciones"]),
            ),
        }

    def _aprendizaje(self) -> dict[str, ResultadoKPI]:
        niveles = self._crudo["niveles"]
        autocorreccion = self._crudo.get(
            "autocorreccion", {"detectadas": 0, "confirmadas": 0}
        )
        return {
            "aprendizaje.escalamiento_de_ayuda": self._proporcion(
                "aprendizaje.escalamiento_de_ayuda",
                (niveles["escalados"], niveles["con_nivel"]),
                faltantes=niveles["sin_nivel"],
            ),
            "aprendizaje.autocorreccion": self._proporcion(
                "aprendizaje.autocorreccion",
                (autocorreccion["confirmadas"], autocorreccion["detectadas"]),
            ),
        }

    def _recuperacion(self) -> dict[str, ResultadoKPI]:
        recuperacion = self._crudo["recuperacion"]
        material = self._crudo["material"]
        bloques = self._crudo["bloques"]
        apertura = self._crudo["apertura_de_fuentes"]
        elegibles = recuperacion["elegibles"]
        referencias = self._crudo.get("referencias_conceptuales", {})
        return {
            "recuperacion.referencias_conceptuales": self._proporcion(
                "recuperacion.referencias_conceptuales",
                (referencias.get("con_referencia", 0), referencias.get("elegibles", 0)),
            ),
            "recuperacion.cobertura": self._proporcion(
                "recuperacion.cobertura", (recuperacion["con_material"], elegibles)
            ),
            "recuperacion.tasa_sin_fuente": self._proporcion(
                "recuperacion.tasa_sin_fuente", (recuperacion["sin_fuente"], elegibles)
            ),
            "recuperacion.diversidad_de_fuentes": self._conteo(
                "recuperacion.diversidad_de_fuentes",
                material["fragmentos"],
                elegibles,
                {"obras": material["obras"]},
            ),
            "recuperacion.concentracion_documental": self._proporcion(
                "recuperacion.concentracion_documental",
                (material["apariciones_top5"], material["apariciones_totales"]),
            ),
            "recuperacion.apertura_de_fuentes": self._proporcion(
                "recuperacion.apertura_de_fuentes",
                (apertura["abiertas"], apertura["elegibles"]),
            ),
            "recuperacion.bloques_verificados": self._proporcion(
                "recuperacion.bloques_verificados",
                (bloques["verificados"], bloques["verificables"]),
            ),
            "recuperacion.derivacion_a_supervision": self._proporcion(
                "recuperacion.derivacion_a_supervision",
                (self._crudo["supervision"]["derivados"], recuperacion["elegibles"]),
            ),
        }

    def _supervision(self) -> dict[str, ResultadoKPI]:
        supervision = self._crudo["supervision"]
        revisados = supervision["revisados"]
        activos_ids = {e["estudiante"] for e in self._crudo["estudiantes"] if e["turnos"]}
        activos = len(activos_ids)
        revisados_activos = activos_ids.intersection(
            supervision.get("estudiantes_revisados_ids", ())
        )
        clases = self._crudo["clases"]
        desde, hasta = self._contexto.periodo.desde, self._contexto.periodo.hasta
        frescas = [
            c for c in clases
            if c["unidad"] and c["actualizado"] is not None and desde <= c["actualizado"] < hasta
        ]
        antiguedad = None
        if supervision["mas_antiguo"] is not None:
            antiguedad = (hasta - supervision["mas_antiguo"]).total_seconds() / 3600
        return {
            "supervision.tiempo_de_atencion": self._distribucion(
                "supervision.tiempo_de_atencion", supervision["horas"]
            ),
            "supervision.tasa_de_intervencion": self._proporcion(
                "supervision.tasa_de_intervencion",
                (supervision["editados"] + supervision["rechazados"], revisados),
            ),
            "supervision.aprobacion_directa": self._proporcion(
                "supervision.aprobacion_directa", (supervision["aprobados"], revisados)
            ),
            "supervision.carga_pendiente": self._conteo(
                "supervision.carga_pendiente",
                supervision["pendientes"],
                len(clases),
                {"antiguedad_del_mas_viejo_horas": antiguedad},
            ),
            "supervision.cobertura": self._proporcion(
                "supervision.cobertura",
                (len(revisados_activos), activos),
                faltantes=supervision["sin_atribucion"],
            ),
            "supervision.actualizacion_curricular": self._proporcion(
                "supervision.actualizacion_curricular", (len(frescas), len(clases))
            ),
        }

    def _institucion(self) -> dict[str, ResultadoKPI]:
        estudiantes = self._crudo["estudiantes"]
        clases = self._crudo["clases"]
        docentes = self._crudo["docentes"]
        versiones = self._crudo["versiones"]
        elegibles = len(estudiantes)
        activos = [e for e in estudiantes if e["turnos"]]
        corpus = sorted({v["corpus"] for v in versiones if v["corpus"]})
        modelos = sorted({v["modelo"] for v in versiones if v["modelo"]})
        return {
            "institucion.docentes_activos": self._conteo(
                "institucion.docentes_activos",
                len({c["docente"] for c in clases if c["activos"]}),
                len({c["docente"] for c in clases}),
            ),
            "institucion.estudiantes_activos_por_clase": self._distribucion(
                "institucion.estudiantes_activos_por_clase",
                [float(c["activos"]) for c in clases],
            ),

            "institucion.cobertura_clases_por_facultad": _con_detalle(
                self._proporcion(
                    "institucion.cobertura_clases_por_facultad",
                    (sum(1 for c in clases if c["facultad_docente"]), len(clases)),
                ),
                {"desglose": _recuento(clases, "facultad_docente")},
            ),
            "institucion.cobertura_clases_por_programa": _con_detalle(
                self._proporcion(
                    "institucion.cobertura_clases_por_programa",
                    (sum(1 for e in estudiantes if e["programa"]), elegibles),
                ),
                {"desglose": _recuento(estudiantes, "programa")},
            ),
            "institucion.perfiles_estudiante_incompletos": self._proporcion(
                "institucion.perfiles_estudiante_incompletos",
                (
                    sum(
                        1 for e in estudiantes
                        if not e["facultad"] or not e["programa"] or not e["semestre"]
                    ),
                    elegibles,
                ),
            ),
            "institucion.completitud_perfiles_docentes": self._proporcion(
                "institucion.completitud_perfiles_docentes",
                (docentes["completos"], docentes["total"]),
            ),
            "institucion.clases_sin_actividad": self._proporcion(
                "institucion.clases_sin_actividad",
                (sum(1 for c in clases if not c["activos"]), len(clases)),
            ),
            "institucion.distribucion_tamano_de_clase": self._distribucion(
                "institucion.distribucion_tamano_de_clase",
                [float(c["matriculados"]) for c in clases],
            ),
            "institucion.matriculados_sin_activar": self._proporcion(
                "institucion.matriculados_sin_activar",
                (elegibles - len(activos), elegibles),
            ),
            "institucion.versiones_de_corpus": self._conteo(
                "institucion.versiones_de_corpus",
                len(corpus),
                sum(v["turnos"] for v in versiones),
                {"reparto": [{"version": v, "turnos": t} for v, t in _reparto(versiones, "corpus")]},
            ),
            "institucion.versiones_de_modelo": self._conteo(
                "institucion.versiones_de_modelo",
                len(modelos),
                sum(v["turnos"] for v in versiones),
                {"reparto": [{"version": v, "turnos": t} for v, t in _reparto(versiones, "modelo")]},
            ),
            "institucion.recuperacion_tras_cambio_de_corpus": self._cambio_de_corpus(),
        }

    def _cambio_de_corpus(self) -> ResultadoKPI:
        definicion = cat.buscar("institucion.recuperacion_tras_cambio_de_corpus")
        cobertura = self._crudo["cobertura_por_corpus"]
        if len(cobertura) < 2:
            return medidas.sin_datos(definicion, self._contexto)
        ultima, anterior = cobertura[0], cobertura[1]
        previa = (
            anterior["con_fuente"] / anterior["turnos"] if anterior["turnos"] else None
        )
        resultado = medidas.proporcion(
            definicion, self._contexto, (ultima["con_fuente"], ultima["turnos"])
        )
        return _con_detalle(
            resultado,
            {
                "version_actual": ultima["corpus"],
                "version_anterior": anterior["corpus"],
                "cobertura_anterior": previa,
                "diferencia": (
                    None
                    if previa is None or resultado.medicion.valor is None
                    else resultado.medicion.valor - previa
                ),
            },
        )

    def armar(self, alcance: Alcance, codigos: tuple[str, ...]) -> list[ResultadoKPI]:
        continuacion = self._crudo.get("continuacion", {})
        sin_retorno = self._crudo.get("sin_retorno_7d", {})
        fenomenos = self._crudo.get("fenomenos_anteproyecto", {})
        calculados: dict[str, ResultadoKPI] = {
            "conductual.ansiedad_matematica": _con_detalle(self._proporcion(
                "conductual.ansiedad_matematica", fenomenos.get("ansiedad", (0, 0))),
                detalle_cobertura("conductual.ansiedad_matematica", {}, fenomenos.get("ansiedad", (0, 0)))),
            "aprendizaje.concepciones_dos_niveles": _con_detalle(
                self._proporcion("aprendizaje.concepciones_dos_niveles",
                                  fenomenos.get("concepciones", (0, 0)), fenomenos.get("trazas_faltantes", 0)),
                {"por_concepcion": fenomenos.get("por_concepcion", {}),
                 "trazas_faltantes": fenomenos.get("trazas_faltantes", 0),
                 **detalle_cobertura("aprendizaje.concepciones_dos_niveles", fenomenos.get("cobertura", {}),
                                    fenomenos.get("concepciones", (0, 0)), fenomenos.get("trazas_faltantes", 0))}),
            "conductual.reiteracion_tras_correccion": _con_detalle(
                self._proporcion("conductual.reiteracion_tras_correccion",
                                  fenomenos.get("reiteracion", (0, 0)), fenomenos.get("trazas_faltantes", 0)),
                {"trazas_faltantes": fenomenos.get("trazas_faltantes", 0),
                 **detalle_cobertura("conductual.reiteracion_tras_correccion", fenomenos.get("cobertura", {}),
                                    fenomenos.get("reiteracion", (0, 0)), fenomenos.get("trazas_faltantes", 0))}),
            "conductual.abandono_de_conversacion": _con_detalle(
                self._proporcion("conductual.abandono_de_conversacion", (
                    sin_retorno.get("sin_retorno", 0), sin_retorno.get("elegibles", 0),
                )), {"censuradas": sin_retorno.get("censuradas", 0), "ventana_dias": 7},
            ),
            "conductual.continuacion_observable": _con_detalle(
                self._proporcion("conductual.continuacion_observable", (
                    continuacion.get("continuadas", 0), continuacion.get("elegibles", 0),
                )), {"censuradas": continuacion.get("censuradas", 0), "ventana_horas": 24},
            ),
            **self._adopcion(),
            **self._aprendizaje(),
            **self._recuperacion(),
            **self._supervision(),
            **self._institucion(),
        }
        pedidos = set(codigos)
        observables = self._crudo.get("observables_dialogo")
        calculados.update({r.definicion.codigo: r for r in calcular_factores(
            self._crudo.get("factores_hibridos", {}), self._contexto)})
        if observables is not None:
            calculados.update({r.definicion.codigo: r for r in calcular_observables(observables, self._contexto)})
        salida: list[ResultadoKPI] = []
        for definicion in cat.para_alcance(alcance):
            if pedidos and definicion.codigo not in pedidos:
                continue
            resultado = calculados.get(definicion.codigo)
            if resultado is None:
                resultado = medidas.no_instrumentado(definicion, self._contexto)
            salida.append(resultado)
        return salida

def _reparto(versiones: list[dict], clave: str) -> list[tuple[str, int]]:
    acumulado: dict[str, int] = {}
    for fila in versiones:
        valor = fila[clave]
        if valor:
            acumulado[valor] = acumulado.get(valor, 0) + fila["turnos"]
    return sorted(acumulado.items(), key=lambda par: (-par[1], par[0]))

def _recuento(filas: list[dict], clave: str) -> list[dict]:
    acumulado: dict[str, int] = {}
    for fila in filas:
        valor = fila.get(clave) or ""
        if valor:
            acumulado[valor] = acumulado.get(valor, 0) + 1
    return [
        {"valor": valor, "cantidad": cantidad}
        for valor, cantidad in sorted(acumulado.items(), key=lambda par: (-par[1], par[0]))
    ]

def _con_detalle(resultado: ResultadoKPI, detalle: dict) -> ResultadoKPI:
    from dataclasses import replace

    medicion = replace(resultado.medicion, detalle={**resultado.medicion.detalle, **detalle})
    return replace(resultado, medicion=medicion)

def contexto_de(periodo: Any, calculado_en: Any, filtros: dict) -> ContextoDeCalculo:
    return ContextoDeCalculo(periodo=periodo, calculado_en=calculado_en, filtros=filtros)
