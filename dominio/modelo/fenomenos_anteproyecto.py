from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime

from dominio.kpi import catalogo, medidas
from dominio.kpi.contratos import ContextoDeCalculo, Periodo
from dominio.pedagogia.confirmacion import base_de_ejercicio

CONCEPCIONES_COMPROMETIDAS = frozenset({"M16", "M21", "M22", "M23"})
ESTRATEGIAS_CORRECTIVAS = frozenset({
    "scaffolding_kq", "conflicto_conceptual", "desarrollo_guiado",
})


def _metadatos(trazas: object, filtro: str) -> dict:
    if not isinstance(trazas, list):
        return {}
    for traza in trazas:
        if isinstance(traza, dict) and traza.get("filtro") == filtro:
            datos = traza.get("metadatos")
            return datos if isinstance(datos, dict) else {}
    return {}

def _intento_verificable(trazas: list) -> tuple[str, str, str] | None:
    intento = _metadatos(trazas, "verificación del intento del estudiante")
    base, propuesta = intento.get("base"), intento.get("propuesta")
    if base is None:
        base = _base_historica(intento.get("ejercicio_activo"))
    veredicto = intento.get("veredicto")
    if (isinstance(base, str) and base.strip() and isinstance(propuesta, str)
            and propuesta.strip() and veredicto in ("valida", "invalida")):
        return base, propuesta, veredicto
    return None

def _base_historica(activo: object) -> str:
    if not isinstance(activo, dict) or activo.get("tipo") not in ("limite", "derivada"):
        return ""
    if not isinstance(activo.get("expresion"), str) or not activo["expresion"].strip():
        return ""
    if activo["tipo"] == "limite" and activo.get("destino") in (None, ""):
        return ""
    return base_de_ejercicio(activo)

def resumir_trazas(registros: list[dict]) -> dict:
    ofrecidos = clasificados = intentos_verificables = correcciones = 0
    concepciones = Counter()
    oportunidades = reincidencias = 0
    pendientes: dict[tuple[str, str, str], str] = {}
    trazas_legibles = 0
    for registro in registros:
        trazas = registro.get("trazas")
        if not isinstance(trazas, list):
            continue
        trazas_legibles += 1
        ofrecimiento = _metadatos(trazas, "ofrecimiento del ítem de dos niveles")
        if ofrecimiento.get("procede") is True:
            ofrecidos += 1
        diagnostico = _metadatos(trazas, "diagnóstico conceptual de dos niveles")
        if diagnostico.get("diagnosticado") is True:
            clasificados += 1
            codigo = diagnostico.get("concepcion")
            if codigo in CONCEPCIONES_COMPROMETIDAS:
                concepciones[codigo] += 1

        intento = _intento_verificable(trazas)
        if intento is None:
            continue
        base, propuesta, veredicto = intento
        decision = _metadatos(trazas, "selección de estrategia")
        intentos_verificables += 1
        clave = (str(registro.get("estudiante", "")), str(registro.get("sesion", "")),
                 "".join(base.lower().split()))
        forma = "".join(propuesta.lower().split())
        anterior = pendientes.pop(clave, None)
        if anterior is not None:
            oportunidades += 1
            if veredicto == "invalida" and forma == anterior:
                reincidencias += 1
        verificacion = _metadatos(trazas, "verificación simbólica")
        correccion_comprobada = verificacion.get("correccion_del_resultado_entregada") is True
        if veredicto == "invalida" and (decision.get("estrategia") in ESTRATEGIAS_CORRECTIVAS or correccion_comprobada):
            correcciones += 1
            pendientes[clave] = forma

    return {
        "trazas_legibles": trazas_legibles,
        "sondeos_ofrecidos": ofrecidos,
        "clasificados": clasificados,
        "concepciones_detectadas": sum(concepciones.values()),
        "por_concepcion": dict(sorted(concepciones.items())),
        "intentos_verificables": intentos_verificables,
        "correcciones_candidatas": correcciones,
        "oportunidades_tras_correccion": oportunidades,
        "reincidencias": reincidencias,
        "patron_reiterado": reincidencias >= 2,
    }

def indicadores_individuales(indicios: dict, resumen: dict, periodo: dict,
                             clase: str, faltantes_traza: int = 0) -> list[dict]:

    tension = next((c for c in indicios.get("componentes", [])
                    if c.get("clave_origen") == "PS-Anx"), {})
    especificaciones = (
        ("conductual.ansiedad_matematica",
         (tension.get("numerador", 0), tension.get("denominador", 0)), {}),
        ("aprendizaje.concepciones_dos_niveles",
         (resumen["concepciones_detectadas"], resumen["clasificados"]),
         {"por_concepcion": resumen["por_concepcion"], "trazas_faltantes": faltantes_traza}),
        ("conductual.reiteracion_tras_correccion",
         (resumen["reincidencias"], resumen["oportunidades_tras_correccion"]),
         {"patron_reiterado": resumen["patron_reiterado"],
          "trazas_faltantes": faltantes_traza}),
    )
    contexto = ContextoDeCalculo(
        Periodo(desde=datetime.fromisoformat(periodo["desde"]),
                hasta=datetime.fromisoformat(periodo["hasta"])),
        datetime.now(UTC), {"clase": clase},
    )
    salida = []
    for codigo, partes, detalle in especificaciones:
        original = catalogo.buscar(codigo)
        definicion = replace(
            original, muestra_minima=1,
            instrumento=replace(original.instrumento, minimo_de_observaciones=1),
        )
        faltantes = detalle.get("trazas_faltantes", 0)
        resultado = medidas.proporcion(definicion, contexto, partes, faltantes).como_json()
        detalle.update(detalle_cobertura(codigo, resumen, partes, faltantes))
        resultado["detalle"] = detalle
        if detalle.get("trazas_faltantes"):
            resultado["advertencias"].append(
                f"{faltantes_traza} trazas no legibles quedaron fuera del cálculo."
            )
        salida.append(resultado)
    return salida

def detalle_cobertura(codigo: str, resumen: dict, partes: tuple,
                     faltantes: int = 0) -> dict:

    x, n = partes
    if codigo == "conductual.ansiedad_matematica":
        motivo = (f"Se analizaron {n} mensajes elegibles; {x} contienen lenguaje reconocido. "
                  "Cero coincidencias no demuestra ausencia de tensión.") if n else (
            "No hay mensajes educativos completos con productor conductual histórico "
            "y habilitación vigente en este periodo."
        )
        return {"motivo_cobertura": motivo}
    cobertura = {k: resumen.get(k, 0) for k in (
        "trazas_legibles", "sondeos_ofrecidos", "clasificados", "intentos_verificables",
        "correcciones_candidatas", "oportunidades_tras_correccion",
    )}
    if faltantes:
        motivo = (f"No se pudieron leer {faltantes} trazas. Hay conteos parciales, "
                  "pero no se publica un porcentaje hasta completar la lectura.")
    elif codigo == "aprendizaje.concepciones_dos_niveles":
        motivo = (f"Se clasificaron {n} respuestas con resultado y razón; {x} recibieron "
                  "uno de los códigos M16, M21, M22 o M23.") if n else (
            f"Sondeos ofrecidos: {cobertura['sondeos_ofrecidos']}; respuestas clasificadas: 0. "
            "El diagnóstico digital actual usa ítems de derivadas. La ficha de límites "
            "L-01 en papel no se incorpora automáticamente a este indicador."
        )
    else:
        motivo = (f"Se observaron {n} nuevos intentos verificables tras una corrección "
                  f"candidata; {x} repitieron la misma respuesta incorrecta.") if n else (
            f"Correcciones candidatas: {cobertura['correcciones_candidatas']}; "
            "nuevos intentos verificables posteriores para el mismo problema: 0. "
            "Pedir «de nuevo» o «no entendí» no demuestra reiteración del error."
        )
    return {"motivo_cobertura": motivo, **cobertura}
