"""Indicios del periodo: frecuencia léxica observable, nunca estado psicológico.

Recalcular sobre historial elegible permite inspeccionar periodos anteriores.
No modifica el perfil adaptativo ni su memoria exponencial ni sus umbrales.
"""
from dominio.deteccion.patrones import VERSION_BANCO, extraer
from dominio.kpi.instrumentos import FUNDAMENTO

VERSION = "indicios-observables.prototipo.v2"
ROTULOS = {
    "PS-Anx": "Lenguaje de tensión al resolver",
    "FAH": "Lenguaje de reticencia a pedir ayuda",
    "autoeficacia": "Lenguaje de baja confianza en la propia capacidad",
}


def resumir_lenguaje(textos) -> dict:
    conteos = dict.fromkeys(ROTULOS, 0)
    n = 0
    for texto in textos:
        if not isinstance(texto, str) or not texto.strip():
            continue
        n += 1
        for clave in extraer(texto):
            if clave in conteos:
                conteos[clave] += 1
    componentes = []
    for clave, x in conteos.items():
        componentes.append({
            "clave_origen": clave, "nombre": ROTULOS[clave],
            "valor": x / n if n else None, "numerador": x, "denominador": n,
            "estado": "disponible" if n else "sin_datos", "unidad": "proporcion",
            "metodologia": {
                "pregunta": f"¿Qué proporción de mensajes contiene {ROTULOS[clave].lower()} reconocido por el detector?",
                "formula": "p = mensajes con al menos una coincidencia / mensajes analizables",
                "formula_latex": r"p=\frac{\sum_{t=1}^{n}\mathbf{1}(o_t>0)}{n}",
                "simbolos": {"p": "proporción observada; 100p es el porcentaje", "o_t": "máximo peso de los patrones coincidentes del mensaje t; cero si no hay coincidencia", "\\mathbf{1}(o_t>0)": "vale uno si hay alguna coincidencia y cero si no; no mide intensidad", "n": "mensajes del estudiante en turnos educativos completos y elegibles"},
                "ejemplo": "2 mensajes con coincidencia entre 10 analizables: 2/10=20%. Varias coincidencias en un mensaje cuentan una sola vez.",
                "alto": "Mayor frecuencia de lenguaje reconocido por las reglas, no mayor intensidad de un estado psicológico.",
                "bajo": "Menor frecuencia reconocida. Cero significa ninguna coincidencia; no demuestra ausencia del constructo.",
                "ausente": "Sin mensajes analizables no hay porcentaje.",
                "incertidumbre": "Detector léxico parcial: puede confundir negaciones, ironía o citas y omitir lenguaje implícito. Solo se analizan conversaciones con traza conductual histórica; esa selección puede sesgar la frecuencia y no representa todo el lenguaje del estudiante. No está calibrado; no se estima confianza psicológica.",
                "fuentes": [f"Mensajes educativos del periodo en conversaciones con traza conductual; detector {VERSION_BANCO}. Relectura con la versión actual, no reconstrucción de decisiones históricas."],
                "recoleccion": "Exige habilitación actual, mayoría de edad y traza histórica del productor conductual. Sin traza no se reconstruye el perfil. El texto no se devuelve en esta ficha.",
                "items": [], "regla_agregacion": "Un voto por mensaje; no se suma entre constructos.",
                "fundamento": FUNDAMENTO, "prototipo": True, "version": VERSION,
            },
        })
    return dict(estado="disponible" if n else "sin_datos", alcance="periodo_consultado",
                version=VERSION, confianza_calibrada=None, observaciones=n,
                componentes=componentes, trazabilidad_turno="historial_elegible")
