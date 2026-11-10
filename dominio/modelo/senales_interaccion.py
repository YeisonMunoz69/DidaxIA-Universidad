from __future__ import annotations

import re
import unicodedata

from dominio.deteccion.patrones import extraer

VERSION = "observables-dialogo.v1"
_CITAS = re.compile(r'"[^"\n]*"|«[^»\n]*»|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\'[^\'\n]*\'(?!\w)')
_NEGACION = re.compile(r"\b(?:no|nunca|tampoco)(?:\s+\w+){0,3}\s*$")
_REGLAS = {
    "ayuda": r"\b(?:ayudame|explicame|explicalo|explicamelo|resuelvelo|resuelve\s+(?:el|este)|como\s+(?:se\s+)?(?:deriv\w*|resuel\w*|calcul\w*|simplific\w*|factoriz\w*|continu\w*|emp\w*)|que\s+(?:es|significa)|por\s+que|pq|verifica|rectifica|revisa\s+(?:mi|el)|dame\s+(?:un|una|la|el)|necesito\s+(?:ayuda|una?\s+guia))\b",
    "dificultad": r"\b(?:no\s+se(?=\s+(?:como|por\s+(?:donde|que)|que|si|con\s+que)\b|\s*[.!?]?$)|no\s+(?:entiendo|entendi|comprendo|comprendi|puedo\s+(?:avanzar|seguir|empezar)|pude\s+(?:avanzar|seguir))|nose|estoy\s+perdid[oa]|me\s+bloqu(?:eo|ee|ie)|perdi\s+el\s+hilo|no\s+me\s+cuadra)\b",
    "aplazamiento": r"\b(?:no\s+quiero\s+(?:seguir|continuar|resolver)|lo\s+dejo\s+(?:para\s+(?:despues|luego)|ahi)|me\s+rindo|prefiero\s+no\s+seguir)\b",
    "reconocimiento_error": r"\b(?:me\s+equivoque|(?:mi|el|ese)\s+(?:resultado|procedimiento)\s+(?:estaba|esta)\s+mal|ya\s+(?:lo\s+)?corregi|ya\s+me\s+di\s+cuenta\s+que\s+estaba\s+mal)\b",
}
_FORMATOS = {
    "explicacion": r"\b(?:explicame|explicalo|explicamelo|explicacion\s+directa|sin\s+(?:mas\s+)?preguntas)\b",
    "paso": r"\b(?:paso\s+a\s+paso|siguiente\s+paso|como\s+(?:continuo|continuar|seguir)|guia|pista)\b",
    "ejemplo": r"\b(?:dame|ponme|muestrame|quiero)\b.{0,45}\b(?:ejemplo|ejercicio\s+parecido)\b",
    "solucion": r"\b(?:dame\s+(?:la\s+)?(?:respuesta|solucion)|resuelvelo|resuelve\s+(?:el|este)|solucion\s+completa)\b",
    "grafica": r"(?:^\W*|\b(?:por\s+favor|puedes|podrias|quiero|necesito)\s+(?:que\s+)?(?:me\s+)?)(?:grafica(?:r)?|graficame|dibuja(?:r)?)\b|\b(?:dame|muestrame|quiero\s+ver)\s+(?:(?:la|una)\s+grafica|.{0,60}\by\s+(?:la|una)\s+grafica)\b",
    "resumen": r"\b(?:resume|resumelo|resumen|sintetiza\w*|mas\s+cort[oa]|en\s+forma\s+corta)\b",
}


_CONCEPTOS = {
    "LIM-01": ("Atribuye inexistencia del límite a 0/0", r"0\s*/\s*0.{0,70}(?:limite\s+no\s+existe|no\s+existe\s+el\s+limite|no\s+hay\s+limite)"),
    "LIM-02": ("Equipara función no definida con límite inexistente", r"(?:funcion|f\s*\([^)]{1,20}\)).{0,25}no\s+(?:esta\s+)?definid[oa].{0,60}(?:limite\s+no\s+existe|no\s+existe\s+el\s+limite)"),
    "LIM-03": ("Atribuye límite cero a que todos los términos tienen x", r"(?:todos\s+los\s+terminos\s+tienen\s+x|todo\s+tiene\s+x).{0,60}(?:limite\s+(?:es|da)\s+(?:0|cero))"),
    "DER-01": ("Afirma que la derivada de una constante es la misma constante", r"derivada\s+de\s+(?:una\s+|la\s+)?constante\s+es\s+(?:la\s+misma\s+constante|ella\s+misma)"),
    "DER-02": ("Afirma que la derivada del producto es el producto de derivadas", r"derivada\s+(?:de\s+un|del)\s+producto\s+es\s+(?:el\s+)?producto\s+de\s+(?:las\s+)?derivadas"),
}
CONCEPTOS = {codigo: nombre for codigo, (nombre, _) in _CONCEPTOS.items()}


def _plano(texto: str) -> str:
    sin_citas = _CITAS.sub(lambda m: " " * len(m.group()), texto)
    plano = "".join(c for c in unicodedata.normalize("NFD", sin_citas.lower())
                    if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", plano).strip()

def _coincide(texto: str, patron: str) -> bool:
    for m in re.finditer(patron, texto):
        prefijo = re.split(r"[.,;!?]", texto[:m.start()])[-1]
        if _NEGACION.search(prefijo) is None:
            return True
    return False

def observar(texto: str) -> dict:
    if not isinstance(texto, str) or not texto.strip():
        return {"senales": [], "formatos": [], "conceptos_candidatos": []}
    plano = _plano(texto)
    senales = [clave for clave, regla in _REGLAS.items() if _coincide(plano, regla)]
    peticion = re.search(r"\b(?:explicame|explicalo|explicamelo|resuelve\w*|dame|ponme|muestrame|quiero|necesito|puedes|podrias|resume\w*|sintetiza\w*|como\s+(?:continuo|continuar|seguir))\b|[?¿]|^mas\s+cort[oa]", plano)
    formatos = [clave for clave, regla in _FORMATOS.items()
                if (peticion or clave == "grafica") and _coincide(plano, regla)]
    if formatos or "dificultad" in senales:
        senales = sorted(set(senales) | {"ayuda"})
    if "FAH" in extraer(texto):
        senales.append("reticencia")

    duda = re.search(r"[?¿]|\b(?:sera|supongamos|alguien\s+dijo|no\s+(?:significa|implica)|es\s+falso|no\s+es\s+cierto|aunque|pero)\b", plano)
    conceptos = [] if duda else [codigo for codigo, (_, regla) in _CONCEPTOS.items()
                                if _coincide(plano, regla)]
    return {"senales": sorted(set(senales)), "formatos": formatos,
            "conceptos_candidatos": conceptos}
