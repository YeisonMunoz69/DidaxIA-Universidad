from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


CONSULTA_CONCEPTUAL = "consulta_conceptual"
EXPLICACION_DIRECTA = "explicacion_directa"
SOLICITUD_EJEMPLO = "solicitud_ejemplo"
PRACTICA_GUIADA = "practica_guiada"
INTENTO_RESOLUCION = "intento_resolucion"
PETICION_SOLUCION = "peticion_solucion"
APLICACION_TRANSFERENCIA = "aplicacion_transferencia"
CAMBIO_ESTRATEGIA = "cambio_estrategia"
BLOQUEO_EXPLICITO = "bloqueo_explicito"
AMBIGUA = "ambigua"

CATALOGO: tuple[str, ...] = (
    CONSULTA_CONCEPTUAL,
    EXPLICACION_DIRECTA,
    SOLICITUD_EJEMPLO,
    PRACTICA_GUIADA,
    INTENTO_RESOLUCION,
    PETICION_SOLUCION,
    APLICACION_TRANSFERENCIA,
    CAMBIO_ESTRATEGIA,
    BLOQUEO_EXPLICITO,
    AMBIGUA,
)

ORIGEN_REGLA = "regla"
ORIGEN_SIN_RESOLVER = "sin_resolver"


CONCEPTUAL = "conceptual"
PROCEDIMENTAL = "procedimental"
EMOCIONAL = "emocional"

_FAMILIA = {
    CONSULTA_CONCEPTUAL: CONCEPTUAL,
    EXPLICACION_DIRECTA: CONCEPTUAL,
    SOLICITUD_EJEMPLO: PROCEDIMENTAL,
    PRACTICA_GUIADA: PROCEDIMENTAL,
    INTENTO_RESOLUCION: PROCEDIMENTAL,
    PETICION_SOLUCION: PROCEDIMENTAL,
    APLICACION_TRANSFERENCIA: PROCEDIMENTAL,
    CAMBIO_ESTRATEGIA: PROCEDIMENTAL,
    BLOQUEO_EXPLICITO: EMOCIONAL,
    AMBIGUA: AMBIGUA,
}


def familia_de(clase: str) -> str:
    return _FAMILIA.get(clase, AMBIGUA)

def _plano(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

def _p(patron: str) -> re.Pattern:
    return re.compile(patron, re.IGNORECASE)

_CAMBIO_ESTRATEGIA = _p(
    r"\b(?:de\s+otra\s+(?:forma|manera)|de\s+otro\s+modo|otra\s+explicacion|"
    r"deja\s+de\s+(?:preguntar|hacerme\s+preguntas)|ya\s+no\s+me\s+preguntes|"
    r"no\s+me\s+hagas\s+mas\s+preguntas|en\s+vez\s+de\s+preguntar|"
    r"prefiero\s+que|preferiria\s+que|mejor\s+explicame|cambia\s+de\s+(?:metodo|forma)|"
    r"explicalo\s+distinto|otro\s+ejemplo|otra\s+representacion|"
    r"(?:voy\s+a\s+)?cambiar\s+de\s+estrategia|no\s+te\s+desvies|"
    r"ese\s+no\s+es\s+mi\s+ejercicio|perdi\s+el\s+hilo)\b"
)


_PETICION_SOLUCION = _p(
    r"\b(?:dime\s+la\s+(?:respuesta|solucion)|dame\s+la\s+(?:respuesta|solucion)|"
    r"solo\s+dime|resuelvelo|resuelvemelo|hazlo\s+tu|hazmelo|"
    r"dame\s+el\s+resultado|dime\s+el\s+resultado|hazme\s+el\s+ejercicio|"
    r"muestrame\s+la\s+solucion|escribeme\s+la\s+respuesta)\b"
)


_BLOQUEO = _p(
    r"\b(?:no\s+se\s+por\s+donde\s+(?:empezar|empiezo|iniciar)|no\s+se\s+como\s+(?:empezar|iniciar)|"
    r"no\s+se\s+empezar|no\s+entiendo\s+(?:ni\s+)?el\s+primer\s+paso|"
    r"estoy\s+bloquead[oa]|me\s+bloqueo|no\s+puedo\s+avanzar|"
    r"no\s+se\s+que\s+hacer|estoy\s+atascad[oa]|no\s+se\s+ni\s+por\s+donde|"
    r"no\s+tengo\s+idea\s+de\s+por\s+donde|estoy\s+perdid[oa]|"
    r"me\s+(?:bloquie|bloquee)|no\s+pude\s+avanzar|"
    r"no\s+se\s+como\s+(?:seguir|continuar)|nose\s+por\s+odne\s+empezaar)\b"
)

_EJEMPLO = _p(
    r"\b(?:(?:\d+|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|varios|m[aá]s)\s+(?:ejemplos|ejercicios)|"
    r"un\s+ejemplo|algun\s+ejemplo|ejemplo\s+resuelto|ejemplo\s+trabajado|"
    r"un\s+caso\s+resuelto|un\s+ejercicio\s+parecido|ponme\s+un\s+ejemplo|dame\s+un\s+ejemplo|"
    r"muestrame\s+un\s+ejemplo|con\s+un\s+ejemplo)\b"
)

_TRANSFERENCIA = _p(
    r"\b(?:como\s+(?:lo\s+)?aplico|como\s+se\s+aplica|"
    r"esto\s+mismo\s+(?:con|para|en)|lo\s+mismo\s+(?:con|para)|"
    r"y\s+si\s+en\s+vez\s+de|sirve\s+(?:tambien\s+)?para|"
    r"funciona\s+igual\s+(?:con|para|en)|aplicarlo\s+a)\b"
)

_PRACTICA = _p(
    r"\b(?:quiero\s+(?:resolver|derivar|calcular|hacerlo|intentarlo|practicar)|"
    r"acompanam[e]|paso\s+a\s+paso|ayudame\s+a\s+resolver|"
    r"hagamoslo\s+junt[oa]s|conmigo|"
    r"quiero\s+entenderlo|guiame|el\s+primer\s+paso|primer\s+paso|"
    r"(?:dame|dime)\s+como\s+(?:seguir|continuar)|como\s+empiezo|"
    r"(?:verifica|rectifica|analiza)\s+(?:mi\s+procedimiento|lo\s+que\s+(?:hice|desarrolle))|"
    r"simplifique\s+y\s+ahora\s+que\s+hago|continua\s+con\s+el\s+siguiente\s+paso)\b"
)

_EXPLICACION = _p(
    r"\b(?:explicame|explicamelo|explicaselo|me\s+explicas|me\s+lo\s+explicas|"
    r"puedes\s+explicar|quiero\s+que\s+me\s+expliques|explicacion\s+de|"
    r"explicalo|explique|comparame|compara|muestrame\s+la\s+diferencia|"
    r"(?:dame\s+un\s+)?resumen|resume(?:lo)?|sintetiza(?:lo)?)\b"
)


_PROPUESTA = _p(
    r"\b(?:me\s+da(?!\s+(?:miedo|pena|rabia|ansiedad)\b)|me\s+dio|me\s+sale|me\s+salio|me\s+queda|me\s+quedo|"
    r"me\s+sigue\s+dando|sigo\s+con|creo\s+que|pienso\s+que|obtuve|tengo|puse|escribi|"
    r"yo\s+haria|lo\s+que\s+haria|primero\s+habria\s+que|seria|"
    r"empiezo|empece|hice|derive|derivando|entonces|mi\s+resultado|"
    r"el\s+resultado\s+es|resultado\s+final|el\s+limite\s+no\s+existe|no\s+existe|diverge)\b"
)


_PROPUESTA_VERBAL = _p(
    r"\b(?:yo\s+haria|lo\s+que\s+haria|primero\s+habria\s+que|"
    r"creo\s+que\s+hay\s+que|pienso\s+que\s+primero|"
    r"habria\s+que\s+(?:aplicar|usar|derivar|separar)|"
    r"usaria\s+la\s+regla|aplicaria\s+la\s+regla|"
    r"empiezo\s+(?:por|derivando|aplicando|calculando|con)|"
    r"empece\s+(?:por|derivando|aplicando)|"
    r"primero\s+(?:derivo|aplico|calculo|hago|separo|uso))\b"
)


_PROPUESTA_RELACION = _p(r"[=<≤≥]|(?<!-)>")

_CONCEPTUAL_PREGUNTA = _p(
    r"(?:que\s+es\b|que\s+significa\b|como\s+se\s+define\b|"
    r"cual\s+es\s+la\s+definicion|por\s+que\b|para\s+que\s+sirve\b|"
    r"en\s+que\s+se\s+diferencia|que\s+diferencia\s+hay|"
    r"explica\s+que\s+es\b)"
)


_IMPERATIVO_DE_CALCULO = _p(
    r"\b(?:deriva|calcula|resuelve|halla|simplifica|integra|evalua|obten)\b"
)


_CORTESIA = _p(
    r"^\s*(?:hola|buenas|buenos\s+dias|buenas\s+tardes|buenas\s+noches|"
    r"gracias|muchas\s+gracias|ok|okey|vale|perfecto|genial|"
    r"vale\s*,?\s*entendido|entendido|listo|adios|hasta\s+luego|de\s+acuerdo)"
    r"[\s.!¡,]*$"
)

_CONFIRMA_AYUDA = _p(
    r"\b(?:si\s*,?\s*muestramelo|si\s*,?\s*resuelvelo|si\s*,?\s*ensename|"
    r"confirmo|si\s+quiero\s+verlo|si\s*,?\s*enseñamelo|"
    r"si\s*,?\s*quiero\s+la\s+solucion|adelante\s*,?\s*muestramelo)\b"
)

_MENOS_PREGUNTAS = _p(
    r"\b(?:sin\s+(?:hacerme\s+)?preguntas|"
    r"deja\s+de\s+(?:preguntar|hacerme\s+preguntas)|"
    r"no\s+me\s+hagas\s+(?:mas\s+)?preguntas|menos\s+preguntas|"
    r"sin\s+preguntarme|no\s+me\s+preguntes|ya\s+no\s+me\s+preguntes|"
    r"ya\s+preguntaste\s+mucho|no\s+que\s+me\s+expliques\s+o\s+me\s+preguntes)\b"
)

_SIN_ADAPTACION = _p(
    r"\b(?:no\s+(?:te\s+)?adaptes|no\s+adaptes\s+tu\s+estilo|"
    r"respondeme\s+siempre\s+igual|no\s+cambies\s+(?:el|tu)\s+estilo|"
    r"no\s+ajustes\s+tu\s+estilo|trata(?:me)?\s+siempre\s+igual)\b"
)


_REACTIVA_ADAPTACION = _p(
    r"\b(?:(?:ya\s+)?puedes\s+adaptarte|vuelve\s+a\s+adaptarte|"
    r"adapta(?:te)?\s+(?:otra\s+vez|de\s+nuevo)|"
    r"vuelve\s+a\s+ajustar\s+tu\s+estilo|"
    r"ya\s+puedes\s+(?:cambiar|ajustar)\s+(?:el|tu)\s+estilo|"
    r"si\s+puedes\s+adaptarte)\b"
)

_CORRIGE_INFERENCIA = _p(
    r"\b(?:no\s*,?\s*no\s+estoy|no\s+estoy\s+bloquead[oa]|"
    r"no\s+es\s+que\s+no\s+entienda|no\s+me\s+malinterpretes|"
    r"no\s+dije\s+eso|te\s+equivocas\s+conmigo|no\s+es\s+eso)\b"
)


_CARGA_EMOCIONAL = _p(
    r"\b(?:estoy\s+(?:muy\s+)?(?:nervios[oa]|agobiad[oa]|frustrad[oa]|"
    r"estresad[oa]|harto|harta)|me\s+frustra|me\s+estresa|me\s+agobia|"
    r"no\s+puedo\s+con\s+esto|me\s+rindo|me\s+da\s+miedo|"
    r"esto\s+me\s+supera|odio\s+esto|no\s+doy\s+mas)\b"
)


_ESTRATEGIA_PEDIDA = (
    (_p(r"\bejemplo\b"), "ejemplo_trabajado"),

    (_p(r"\b(?:representacion|grafic\w*|dibujo|visual)\b"), "cambio_de_representacion"),
    (_p(r"\b(?:comparame|compara|muestrame\s+la\s+diferencia)\b"), "explicacion_teorica_directa"),
    (
        _p(r"\b(?:explicame\w*|explicalo|explicacion|expliques|explique\w*)\b"),
        "explicacion_teorica_directa",
    ),
    (_p(r"\bpaso\s+a\s+paso|primer\s+paso\b"), "primer_paso_ante_bloqueo"),
)


@dataclass(frozen=True)
class Intencion:

    clase: str = AMBIGUA
    origen: str = ORIGEN_SIN_RESOLVER
    motivo: str = ""

    candidatas: tuple[str, ...] = ()

    descartadas: tuple[tuple[str, str], ...] = ()

    con_matematica: bool = False
    es_cortesia: bool = False
    confirma_ayuda: bool = False
    pide_menos_preguntas: bool = False
    sin_adaptacion: bool = False

    reactiva_adaptacion: bool = False
    corrige_inferencia: bool = False
    carga_emocional_expresada: bool = False

    estrategia_solicitada: str = ""

    propone_solucion: bool = False

    @property
    def familia(self) -> str:
        return familia_de(self.clase)

    def como_dict(self) -> dict:
        return {
            "clase": self.clase,
            "origen": self.origen,
            "motivo": self.motivo,
            "familia": self.familia,
            "candidatas": list(self.candidatas),
            "descartadas": [list(d) for d in self.descartadas],
            "con_matematica": self.con_matematica,
            "es_cortesia": self.es_cortesia,
            "confirma_ayuda": self.confirma_ayuda,
            "pide_menos_preguntas": self.pide_menos_preguntas,
            "sin_adaptacion": self.sin_adaptacion,
            "reactiva_adaptacion": self.reactiva_adaptacion,
            "corrige_inferencia": self.corrige_inferencia,
            "carga_emocional_expresada": self.carga_emocional_expresada,
            "estrategia_solicitada": self.estrategia_solicitada,
            "propone_solucion": self.propone_solucion,
        }

@dataclass(frozen=True)
class _Regla:

    clase: str
    patron: re.Pattern
    motivo: str

    exige_matematica: bool = False

    veta: tuple[re.Pattern, ...] = field(default_factory=tuple)

_REGLAS: tuple[_Regla, ...] = (
    _Regla(CAMBIO_ESTRATEGIA, _CAMBIO_ESTRATEGIA, "pide explícitamente otra forma"),
    _Regla(PETICION_SOLUCION, _PETICION_SOLUCION, "pide la respuesta con todas las letras"),

    _Regla(
        BLOQUEO_EXPLICITO,
        _BLOQUEO,
        "declara que no sabe empezar o no puede avanzar",
        veta=(_CORRIGE_INFERENCIA,),
    ),
    _Regla(SOLICITUD_EJEMPLO, _EJEMPLO, "pide un ejemplo"),
    _Regla(APLICACION_TRANSFERENCIA, _TRANSFERENCIA, "pregunta cómo aplicar lo mismo a otro caso"),
    _Regla(PRACTICA_GUIADA, _PRACTICA, "quiere resolverlo él, acompañado"),
    _Regla(EXPLICACION_DIRECTA, _EXPLICACION, "pide que se le explique"),
    _Regla(
        INTENTO_RESOLUCION,
        _PROPUESTA,
        "propone un resultado o una transformación, con notación",
        exige_matematica=True,
    ),
    _Regla(
        INTENTO_RESOLUCION,
        _PROPUESTA_RELACION,
        "escribe una relación: es un resultado parcial",
        exige_matematica=True,
    ),
    _Regla(
        INTENTO_RESOLUCION,
        _PROPUESTA_VERBAL,
        "propone qué hacer o por qué, sólo con palabras",
    ),
    _Regla(CONSULTA_CONCEPTUAL, _CONCEPTUAL_PREGUNTA, "pregunta por una definición o un porqué"),
    _Regla(
        PETICION_SOLUCION,
        _IMPERATIVO_DE_CALCULO,
        "manda calcular sin pedir acompañamiento: pide el resultado",
        exige_matematica=True,
    ),
)


def _estrategia_pedida(plano: str) -> str:
    for patron, estrategia in _ESTRATEGIA_PEDIDA:
        if patron.search(plano):
            return estrategia
    return ""

def clasificar(texto: str, con_matematica: bool = False) -> Intencion:
    plano = _plano(texto)
    es_cortesia = bool(_CORTESIA.match(plano))
    confirma = bool(_CONFIRMA_AYUDA.search(plano)) and not bool(
        re.search(r"\b(?:no|nunca)\s+confirmo\b", plano)
    )
    señales = {
        "con_matematica": con_matematica,
        "es_cortesia": es_cortesia,
        "confirma_ayuda": confirma,
        "pide_menos_preguntas": bool(_MENOS_PREGUNTAS.search(plano)),
        "sin_adaptacion": bool(_SIN_ADAPTACION.search(plano)),
        "reactiva_adaptacion": bool(_REACTIVA_ADAPTACION.search(plano)),
        "corrige_inferencia": bool(_CORRIGE_INFERENCIA.search(plano)),
        "carga_emocional_expresada": bool(_CARGA_EMOCIONAL.search(plano)),
        "estrategia_solicitada": _estrategia_pedida(plano),
    }

    if es_cortesia:
        return Intencion(
            clase=AMBIGUA,
            origen=ORIGEN_REGLA,
            motivo="cortesía: no pide nada que se pueda atender",
            candidatas=(AMBIGUA,),
            **señales,
        )

    if confirma:
        return Intencion(
            clase=PETICION_SOLUCION,
            origen=ORIGEN_REGLA,
            motivo="confirma la ayuda que el sistema le ofreció (RF-GEN-05)",
            candidatas=(PETICION_SOLUCION,),
            propone_solucion=False,
            **señales,
        )

    candidatas: list[str] = []
    casadas: list[tuple[str, str]] = []
    for regla in _REGLAS:
        if regla.clase not in candidatas:
            candidatas.append(regla.clase)
        if regla.exige_matematica and not con_matematica:
            continue
        if any(v.search(plano) for v in regla.veta):
            continue
        if regla.patron.search(plano):
            casadas.append((regla.clase, regla.motivo))

    propone = any(c == INTENTO_RESOLUCION for c, _ in casadas)

    if not casadas:
        return Intencion(
            clase=AMBIGUA,
            origen=ORIGEN_SIN_RESOLVER,
            motivo="ninguna regla del catálogo v1 casó con este mensaje",
            candidatas=tuple(candidatas),
            propone_solucion=False,
            **señales,
        )

    ganadora, motivo = casadas[0]
    descartadas = tuple(
        (clase, f"casó «{razon}» pero {ganadora} tiene precedencia en la cascada")
        for clase, razon in casadas[1:]
        if clase != ganadora
    )
    return Intencion(
        clase=ganadora,
        origen=ORIGEN_REGLA,
        motivo=motivo,
        candidatas=tuple(candidatas),
        descartadas=descartadas,
        propone_solucion=propone,
        **señales,
    )
