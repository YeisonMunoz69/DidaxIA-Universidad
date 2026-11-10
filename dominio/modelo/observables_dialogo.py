"""Relectura reproducible del diálogo elegible para los KPI propios.

Se consume texto en memoria, nunca se devuelve. La identificación sólo sirve
para evitar duplicados y separar hilos, problemas y pares temporales.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta
from statistics import median

from dominio.kpi import medidas
from dominio.kpi.dimensiones.observables import CATALOGO, PREFIJO
from dominio.modelo.fenomenos_anteproyecto import _intento_verificable
from dominio.modelo.senales_interaccion import CONCEPTOS, VERSION, observar


def _momento(valor):
    try:
        resultado = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
        return resultado if isinstance(resultado, datetime) and resultado.tzinfo else None
    except ValueError:
        return None


def _reintentos(registros, desde, hasta):
    intentos = [
        (r, _intento_verificable(r.get("trazas", [])), _momento(r.get("momento")))
        for r in registros if isinstance(r.get("trazas"), list)
    ]
    ordenados = sorted((fila for fila in intentos if fila[1] and fila[2]),
                       key=lambda fila: (fila[2], str(fila[0].get("turno", ""))))
    pendientes, vistos = {}, set()
    partes = {"error_verificado": [0, 0], "recuperacion": [0, 0], "reintento": [0, 0]}
    censuradas = 0
    for registro, intento, momento in ordenados:
        if not desde <= momento < hasta:
            continue
        identidad = (registro.get("estudiante"), registro.get("sesion"), registro.get("turno"))
        if not all(identidad) or identidad in vistos:
            continue
        vistos.add(identidad)
        base, _, veredicto = intento
        clave = (registro.get("estudiante"), registro.get("sesion"), "".join(base.lower().split()))
        partes["error_verificado"][1] += 1
        partes["error_verificado"][0] += veredicto == "invalida"
        anterior = pendientes.pop(clave, None)
        if anterior is not None:
            partes["recuperacion"][1] += 1
            partes["recuperacion"][0] += veredicto == "valida"
            # Una misma ventana para éxitos y casos sin seguimiento. Un turno
            # reciente no recibe ventaja por tener ya un reintento positivo.
            if anterior + timedelta(hours=24) < hasta:
                partes["reintento"][0] += momento <= anterior + timedelta(hours=24)
        if veredicto == "invalida":
            pendientes[clave] = momento
            if momento + timedelta(hours=24) < hasta:
                partes["reintento"][1] += 1
            else:
                censuradas += 1
    return partes, {"ventana_horas": 24, "episodios_recientes_excluidos": censuradas,
                   "intentos_sin_fecha": sum(bool(i) and not m for _, i, m in intentos)}


def resumir_observables(mensajes, registros, desde, hasta, faltantes_traza=0):
    if desde.tzinfo is None or hasta.tzinfo is None or desde >= hasta:
        raise ValueError("Periodo con zona horaria y orden válido requerido")
    conteos, formatos, conceptos = Counter(), Counter(), Counter()
    pares, vistos = {}, set()
    n = con_formato = sin_fecha = 0
    mitad = desde + (hasta - desde) / 2
    for mensaje in mensajes:
        clave = (mensaje.get("estudiante"), mensaje.get("sesion"), mensaje.get("turno"))
        if not all(clave) or clave in vistos:
            continue
        vistos.add(clave)
        texto = mensaje.get("texto")
        if not isinstance(texto, str) or not texto.strip():
            continue
        momento = _momento(mensaje.get("momento"))
        if momento is not None and not desde <= momento < hasta:
            continue
        n += 1
        observacion = observar(texto)
        conteos.update(observacion["senales"])
        formatos.update(observacion["formatos"])
        conceptos.update(observacion["conceptos_candidatos"])
        conteos["conceptos_candidatos"] += bool(observacion["conceptos_candidatos"])
        con_formato += bool(observacion["formatos"])
        if momento is None:
            sin_fecha += 1
            continue
        fila = pares.setdefault(mensaje["estudiante"], [[0, 0], [0, 0]])
        observada = fila[int(momento >= mitad)]
        observada[1] += 1
        observada[0] += "ayuda" in observacion["senales"]
    partes = {clave: [conteos[clave], n] for clave in (
        "ayuda", "dificultad", "reticencia", "aplazamiento", "reconocimiento_error", "conceptos_candidatos",
    )}
    maximo = max(formatos.values(), default=0)
    partes["preferencia"] = [maximo, con_formato]
    matematicas, detalle_matematico = _reintentos(registros, desde, hasta)
    partes.update(matematicas)
    diferencias = [100 * (seg[0] / seg[1] - pri[0] / pri[1]) for pri, seg in pares.values()
                   if pri[1] >= 5 and seg[1] >= 5]
    return {
        "version": VERSION, "mensajes_analizables": n, "partes": partes,
        "formatos": dict(sorted(formatos.items())),
        "formatos_modales": sorted(k for k, v in formatos.items() if v == maximo),
        "conceptos": {k: {"nombre": CONCEPTOS[k], "mensajes": v} for k, v in sorted(conceptos.items())},
        "matematica": {**detalle_matematico, "trazas_faltantes": faltantes_traza},
        "cambio": {"mediana": median(diferencias) if diferencias else None,
                   "observaciones": len(diferencias), "sin_par": len(pares) - len(diferencias),
                   "mensajes_sin_fecha": sin_fecha, "corte_intermedio": mitad.isoformat()},
    }


def calcular_observables(resumen, contexto, *, individual=False):
    salida = []
    for original in CATALOGO:
        definicion = replace(original, muestra_minima=1,
                             instrumento=replace(original.instrumento, minimo_de_observaciones=1)) if individual else original
        clave = definicion.codigo.removeprefix(PREFIJO)
        if clave == "cambio_ayuda":
            detalle = resumen["cambio"]
            resultado = medidas.distribucion(definicion, contexto, detalle["mediana"], detalle)
            motivo = (f"Personas con cinco mensajes en cada mitad: {detalle['observaciones']}; "
                      f"personas sin par completo: {detalle['sin_par']}. Cambio de lenguaje registrado, no de aprendizaje.")
        else:
            partes = resumen["partes"][clave]
            detalle, faltantes = _detalle(clave, resumen)
            resultado = medidas.proporcion(definicion, contexto, tuple(partes), faltantes)
            motivo = (f"Casos observados: {partes[0]}; oportunidades analizables: {partes[1]}. "
                      "Sin oportunidades no se calcula porcentaje.")
        detalle = {**detalle, "motivo_cobertura": motivo, "version_observables": VERSION}
        if clave in ("error_verificado", "recuperacion", "reintento"):
            detalle["motivo_cobertura"] += " Usa intentos comprobados del mismo hilo y problema; no mide una concepción estable."
        if clave == "conceptos_candidatos":
            detalle["motivo_cobertura"] += " Son afirmaciones tipificadas para revisión, separadas del diagnóstico de dos niveles."
        salida.append(replace(resultado, medicion=replace(resultado.medicion,
                             detalle={**resultado.medicion.detalle, **detalle})))
    return salida


def _detalle(clave, resumen):
    if clave in ("error_verificado", "recuperacion", "reintento"):
        detalle = resumen["matematica"]
        return detalle, detalle["trazas_faltantes"] + detalle["intentos_sin_fecha"]
    if clave == "preferencia":
        return {"formatos": resumen["formatos"], "formatos_modales": resumen["formatos_modales"],
                "solapamientos": "Un mensaje puede pedir varios formatos; las proporciones por formato no se suman."}, 0
    if clave == "conceptos_candidatos":
        return {"por_concepto": resumen["conceptos"]}, 0
    return {}, 0
