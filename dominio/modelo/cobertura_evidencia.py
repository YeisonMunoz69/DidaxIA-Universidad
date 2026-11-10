from __future__ import annotations

from datetime import datetime

VERSION = "cobertura-evidencia.experimental.v1"
FORMULA = (
    "0.30·min(turnos/15,1) + 0.20·min(conversaciones/4,1) + "
    "0.15·min(días_activos/5,1) + 0.20·proporción_válida + "
    "0.15·recencia"
)
FORMULA_LATEX = (
    r"0{,}30\min\left(\frac{\mathrm{turnos}}{15},1\right)"
    r"+0{,}20\min\left(\frac{\mathrm{conversaciones}}{4},1\right)"
    r"+0{,}15\min\left(\frac{\text{días activos}}{5},1\right)"
    r"+0{,}20\,\text{proporción válida}"
    r"+0{,}15\,\mathrm{recencia}"
)
PESOS = {
    "turnos_elegibles": 0.30,
    "conversaciones": 0.20,
    "dias_activos": 0.15,
    "datos_validos": 0.20,
    "recencia": 0.15,
}
MINIMOS = {"turnos_elegibles": 5, "conversaciones": 2, "dias_activos": 2}


def calcular_cobertura_evidencia(
    *,
    turnos_elegibles: int,
    conversaciones: int,
    dias_activos: int,
    respuestas: int,
    respuestas_validas: int,
    ultima_actividad: datetime | None,
    hasta: datetime,
) -> dict:

    observados = {
        "turnos_elegibles": max(0, int(turnos_elegibles)),
        "conversaciones": max(0, int(conversaciones)),
        "dias_activos": max(0, int(dias_activos)),
    }
    faltantes = [
        clave
        for clave, minimo in MINIMOS.items()
        if observados[clave] < minimo
    ]
    base = {
        "version": VERSION,
        "nombre": "Cobertura de evidencia de la estimación",
        "madurez_metodologica": "experimental",
        "escala": "0 a 1",
        "formula": FORMULA,
        "formula_latex": FORMULA_LATEX,
        "pesos": dict(PESOS),
        "muestra_minima": dict(MINIMOS),
        "faltantes": faltantes,
        "interpretacion": (
            "Resume la amplitud de evidencia observable disponible; no mide "
            "certeza psicológica, aprendizaje ni desempeño académico."
        ),
        "limitaciones": [
            "Los umbrales y pesos son heurísticos y todavía no tienen calibración externa.",
            "Más actividad puede aumentar la cobertura sin mejorar el aprendizaje.",
            "No debe usarse como nota, diagnóstico ni criterio automático de decisión.",
        ],
    }
    if faltantes or respuestas <= 0 or ultima_actividad is None:
        return {
            **base,
            "estado": "evidencia_insuficiente",
            "valor": None,
            "componentes": {},
        }

    respuestas = max(0, int(respuestas))
    respuestas_validas = min(respuestas, max(0, int(respuestas_validas)))
    segundos = max(0.0, (hasta - ultima_actividad).total_seconds())
    dias_desde_actividad = segundos / 86400
    if dias_desde_actividad <= 7:
        recencia = 1.0
    elif dias_desde_actividad <= 14:
        recencia = 0.5
    else:
        recencia = 0.0

    componentes = {
        "turnos_elegibles": min(observados["turnos_elegibles"] / 15, 1.0),
        "conversaciones": min(observados["conversaciones"] / 4, 1.0),
        "dias_activos": min(observados["dias_activos"] / 5, 1.0),
        "datos_validos": respuestas_validas / respuestas,
        "recencia": recencia,
    }
    valor = sum(componentes[clave] * PESOS[clave] for clave in PESOS)
    return {
        **base,
        "estado": "disponible",
        "valor": round(valor, 4),
        "componentes": {
            clave: round(componente, 4)
            for clave, componente in componentes.items()
        },
        "observaciones": {
            **observados,
            "respuestas": respuestas,
            "respuestas_validas": respuestas_validas,
            "dias_desde_ultima_actividad": round(dias_desde_actividad, 2),
        },
    }
