from __future__ import annotations

import re
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.deteccion_matematica import hallar_matematica
from dominio.modelo.notacion_entrada import (
    NUMEROS_ESCRITOS,
    normalizar_escritura_matematica,
    normalizar_frase_matematica,
    quitar_delimitadores_matematicos,
)
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import (
    AMBIGUA,
    CONCEPTUAL,
    CONSULTA_CONCEPTUAL,
    EMOCIONAL,
    EXPLICACION_DIRECTA,
    INTENTO_RESOLUCION,
    ORIGEN_REGLA,
    ORIGEN_SIN_RESOLVER,
    PETICION_SOLUCION,
    PRACTICA_GUIADA,
    PROCEDIMENTAL,
    clasificar,
    familia_de,
)

__all__ = [
    "AMBIGUA",
    "CONCEPTUAL",
    "EMOCIONAL",
    "ORIGEN_REGLA",
    "ORIGEN_SIN_RESOLVER",
    "PROCEDIMENTAL",
    "FiltroIntencion",
    "familia_de",
]


_NUMEROS_DESTINO = "|".join(sorted(map(re.escape, NUMEROS_ESCRITOS), key=len, reverse=True))
_DESTINO_LIMITE = rf"(?P<destino>menos\s+infinito|infinito|(?:menos\s+)?(?:{_NUMEROS_DESTINO})|[-+]?\\infty|[-+]?∞|[-+]?oo|[-+]?inf\b|(?:\\pi|π|pi)(?:\s*/\s*\d+)?|[-+]?\d+(?:[.,]\d+)?[+-]?)"
_VARIABLE_LIMITE = r"(?P<variable>[a-zA-Zθ])"


_LIMITE_CUANDO_DE = re.compile(
    rf"l[ií]mite\s+cuando\s+{_VARIABLE_LIMITE}\s*(?:→|->|tiende\s+a|se\s+acerca\s+a)\s*{_DESTINO_LIMITE}\s+de\s+"
    rf"(?P<expresion>[^?!]+)",
    re.IGNORECASE,
)


_LIMITE_DE_CUANDO = re.compile(
    rf"l[ií]mite\s+de\s+(?P<expresion>.+?)\s+cuando\s+{_VARIABLE_LIMITE}\s*(?:→|->|tiende\s+a|se\s+acerca\s+a)\s*"
    rf"{_DESTINO_LIMITE}",
    re.IGNORECASE,
)
_GRAFICA_PARA_LIMITE = re.compile(
    rf"gr[aá]fica\s+de\s+(?P<expresion>.+?)\s+para\s+entender\s+el\s+l[ií]mite\s+"
    rf"cuando\s+{_VARIABLE_LIMITE}\s*(?:→|->|tiende\s+a|se\s+acerca\s+a)\s*"
    rf"{_DESTINO_LIMITE}", re.IGNORECASE,
)
_LIMITE_PARENTESIS = re.compile(
    rf"(?<!\\)\blim\s*\(\s*{_VARIABLE_LIMITE}\s*(?:→|->|\\to)\s*"
    rf"{_DESTINO_LIMITE}\s*\)\s*(?P<expresion>[^?!;$]+)", re.IGNORECASE,
)
_LIMITE_LATEX = re.compile(
    rf"\\lim\s*_\s*\{{\s*{_VARIABLE_LIMITE}\s*\\to\s*{_DESTINO_LIMITE}\s*\}}\s*(?P<expresion>.+)",
    re.IGNORECASE,
)
_LIMITE_BREVE = re.compile(
    rf"(?<!\\)\bl[ií]m(?:ite)?\s+{_VARIABLE_LIMITE}\s*(?:→|->|tiende\s+a)\s*"
    rf"{_DESTINO_LIMITE}\s+(?:de\s+)?(?P<expresion>[^?!$]+)",
    re.IGNORECASE,
)
_LIMITE_SUBINDICE = re.compile(
    rf"(?<!\\)\bl[ií]m\s*_\s*\{{\s*{_VARIABLE_LIMITE}\s*(?:→|->|\\to)\s*"
    rf"{_DESTINO_LIMITE}\s*\}}\s*(?P<expresion>.+)",
    re.IGNORECASE,
)


_LIMITE_COLOQUIAL = re.compile(
    rf"\b(?:tengo|veo|analizo|calculo)\s+(?P<expresion>.+?)\s+cuando\s+"
    rf"(?:la\s+)?{_VARIABLE_LIMITE}\s+(?:se\s+arrima|se\s+acerca|tiende)\s+a\s+"
    rf"{_DESTINO_LIMITE}", re.IGNORECASE,
)


_LIMITE_VARIABLE_CUANDO = re.compile(
    rf"l[ií]mite\s+de\s+{_VARIABLE_LIMITE}\s+cuando\s+(?:tiende|se\s+acerca)\s+a\s*"
    rf"{_DESTINO_LIMITE}\s+(?:para|de|en)\s+(?P<expresion>.+)", re.I,
)
_DERIVADA_EXPLICITA = re.compile(
    r"\b(?:halla\s+la\s+derivada\s+de|calcula\s+la\s+derivada\s+de|"
    r"derivar\s+la\s+funci[oó]n|derivada\s+de|deriva(?:r|ndo)?)\s+"
    r"(?P<expresion>.+)",
    re.IGNORECASE,
)
_DERIVADA_NOTACION = re.compile(
    r"(?:d\s*/\s*dx|\\(?:d|t)?frac\s*\{d\}\s*\{dx\})\s*(?P<expresion>.+)",
    re.IGNORECASE,
)
_VALOR_EXPLICITO = re.compile(
    r"\b(?:eval[uú]a|calcula(?:\s+el\s+valor\s+de)?|cu[aá]nto\s+(?:es|vale))\s+"
    r"(?P<expresion>.+)",
    re.IGNORECASE,
)


def _destino_normalizado(texto: str) -> str:
    plano = texto.strip().lower()
    if "infinito" in plano or "infty" in plano or "∞" in plano or plano.lstrip("+-") in ("oo", "inf"):
        return "-oo" if "menos" in plano or plano.startswith("-") else "oo"
    nombre = plano.removeprefix("menos ")
    if nombre in NUMEROS_ESCRITOS:
        return ("-" if plano.startswith("menos ") else "") + str(NUMEROS_ESCRITOS[nombre])
    return plano.replace(r"\pi", "pi").replace("π", "pi").replace(" ", "").replace(",", ".")

def _funcion_sin_comentario(texto: str) -> str:
    s = texto.strip().strip("$").strip()
    s = re.split(r"[;!?¿¡]|\.(?=\s|$)|,\s*(?=[a-záéíóúñ])|\s+(?:y\s+(?:c[oó]mo|explica\w*|dime|muestra\w*|cuenta\w*|por\s+qu[eé])|"
                 r"con\s+la\s+regla\b|respecto\s+(?:de|a)\b|"
                 r"(?:no\s+s[eé]|c[oó]mo|porque|pero|explicame|expl[ií]came|ay[uú]dame|necesito))\b", s, maxsplit=1, flags=re.I)[0]
    s = re.split(r"\$?\s*ser[ií]a\s+(?:igual\s+a\s+)?", s, maxsplit=1, flags=re.I)[0]
    s = re.split(r"\s+(?:es|vale|da|ser[ií]a|resulta)\s+(?=[-+]?\d|[-+]?∞|[-+]?oo|no\s+existe)",
                 s, maxsplit=1, flags=re.I)[0].strip().rstrip("$.?! ")
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.replace("[", "(").replace("]", ")")
    return normalizar_frase_matematica(s)

def _intento_de_limite(texto: str) -> tuple[str, str, str] | None:
    normalizado = normalizar_escritura_matematica(texto).strip().strip("$").strip()

    normalizado = re.sub(r"(?<=\d)\s*\^\s*(?:\{\s*([+-])\s*\}|\(\s*([+-])\s*\)|([+-]))",
                        lambda m: next(g for g in m.groups() if g), normalizado)

    if len(re.findall(r"(?:\\lim\b|(?<!\\)\blim\s*(?:\(|_|[a-z]\s*(?:->|→))|\bl[ií]mite\s+(?:de(?!\s+lim\b)|cuando))", normalizado, re.I)) > 1:
        return None
    for patron in (
        _LIMITE_VARIABLE_CUANDO,
        _LIMITE_CUANDO_DE, _LIMITE_DE_CUANDO, _GRAFICA_PARA_LIMITE,
        _LIMITE_PARENTESIS, _LIMITE_LATEX, _LIMITE_SUBINDICE, _LIMITE_BREVE,
        _LIMITE_COLOQUIAL,
    ):
        coincidencia = patron.search(normalizado)
        if coincidencia:
            expresion = _funcion_sin_comentario(coincidencia.group("expresion"))
            if expresion:
                return expresion, _destino_normalizado(coincidencia.group("destino")), coincidencia.group("variable")
    return None

def _derivada_de_funcion_declarada(texto: str) -> dict[str, str] | None:
    if not re.search(r"\bderivad[ao]\b|\bderivar\b", texto, re.I):
        return None
    definiciones = list(re.finditer(r"\b[a-zA-Z]\s*\(\s*x\s*\)\s*(?:=|igual(?:\s+a)?\b)\s*", texto))
    if len(definiciones) != 1:
        return None
    expresion = _funcion_sin_comentario(quitar_delimitadores_matematicos(texto[definiciones[0].end():]))
    if not expresion or '=' in expresion:
        return None
    return {"tipo": "derivada", "expresion": expresion, "variable": "x", "destino": ""}

def _quitar_nombre_y_operador_derivada(expresion: str) -> str:
    expresion = quitar_delimitadores_matematicos(expresion)
    if expresion.count("$") % 2 == 0:
        expresion = expresion.replace("$", "")
    expresion = expresion.replace(r"\left", "").replace(r"\right", "")
    expresion = re.sub(r"^(?:d\s*/\s*dx|\\(?:d|t)?frac\s*\{d\}\s*\{dx\})\s*", "", expresion, flags=re.I)
    expresion = quitar_delimitadores_matematicos(expresion)
    expresion = re.sub(r"^(?:la\s+funci[oó]n\s+)?[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)\s*(?:=|igual(?:\s+a)?\b)\s*", "", expresion, flags=re.I)
    expresion = quitar_delimitadores_matematicos(expresion)
    return "" if '=' in expresion else expresion

def extraer_ejercicio_explicito(texto: str) -> dict[str, str] | None:
    limite = _intento_de_limite(texto)
    if limite is not None:
        expresion, destino, variable = limite
        return {"tipo": "limite", "expresion": expresion, "variable": variable, "destino": destino}

    normalizado = normalizar_escritura_matematica(texto).strip()
    if re.search(r"\b(?:me\s+da|me\s+dio|me\s+sale|me\s+queda|resultado\s+es)\b", normalizado, re.I):
        return None
    coincidencia = _DERIVADA_EXPLICITA.search(normalizado) or _DERIVADA_NOTACION.search(normalizado)
    if coincidencia is None and (declarada := _derivada_de_funcion_declarada(normalizado)):
        return declarada
    if coincidencia is None:
        valor = _VALOR_EXPLICITO.search(normalizado)
        if valor is None:
            return None
        expresion = valor.group("expresion").strip().rstrip("?.! ").strip("$")
        expresion = normalizar_frase_matematica(expresion)
        if not expresion or not re.search(r"\d|π|\\(?:frac|sqrt)", expresion):
            return None
        return {"tipo": "valor", "expresion": expresion, "variable": "x", "destino": ""}
    expresion = coincidencia.group("expresion").strip().rstrip("?.! ")
    if re.search(r"\s+(?:es|me\s+da|me\s+dio|me\s+queda|resulta)\s+", expresion, re.I):
        return None
    expresion = re.split(
        r"\s+y\s+(?:explica|dime|muestra|cuenta|por\s+qu[eé])\b",
        expresion, maxsplit=1, flags=re.IGNORECASE,
    )[0]
    expresion = _quitar_nombre_y_operador_derivada(expresion)
    expresion = expresion.replace(r"\left(", "(").replace(r"\right)", ")")
    if re.match(r"por\s+definici[oó]n\b", expresion, re.I):
        return None
    expresion = _funcion_sin_comentario(expresion)
    if not expresion or re.match(r"por\s+definici[oó]n\b|(?:esa|esta|la\s+anterior)\s+funci[oó]n\b", expresion, re.I):
        return None
    return {"tipo": "derivada", "expresion": normalizar_frase_matematica(expresion), "variable": "x", "destino": ""}

def extraer_curva_solicitada(texto: str) -> str:
    normalizado = normalizar_escritura_matematica(texto)
    añadida = re.search(
        r"\b(?:a[nñ]ade|agrega)\b[^.;]*?\b[a-zA-Z]\s*\(\s*x\s*\)\s*=\s*",
        normalizado, re.I,
    )
    directa = re.search(
        r"\b(?:grafica|gr[aá]fica|graficar|dibuja)\s+"
        r"(?:(?:exactamente|la\s+funci[oó]n|de)\s+)?",
        normalizado, re.I,
    )
    marca = añadida or directa
    if not marca:
        return ""
    resto = normalizado[marca.end():]
    expresion = re.split(
        r"\s+(?:cerca|para|pero|como)\b|\.(?!\d)|[;!?]",
        resto, maxsplit=1, flags=re.I,
    )[0].strip().strip('$')

    sin_nombre = re.sub(r"^(?:[a-zA-Z]\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)|y)\s*=\s*", "", expresion, flags=re.I)
    declarada = sin_nombre != expresion
    expresion = sin_nombre
    expresion = normalizar_frase_matematica(expresion)
    return expresion if expresion and (declarada or re.search(r"[xX]", expresion)) else ""

def destino_solicitado_para_limite(texto: str, destino_actual: str = "") -> str:
    patron = re.compile(
        rf"(?<![/\w])x\s*(?:cuando\s+)?(?:→|->|tiende\s+a|se\s+acerca\s+a|acerc[aá]ndose\s+a)\s*"
        rf"{_DESTINO_LIMITE}", re.I,
    )
    coincidencia = patron.search(normalizar_escritura_matematica(texto))
    if coincidencia:
        return _destino_normalizado(coincidencia["destino"])

    if destino_actual and destino_actual not in ("oo", "-oo"):
        punto = destino_actual.rstrip("+-")
        if re.search(r"\b(?:por\s+)?(?:ambos\s+lados|los\s+dos\s+lados|bilateral)\b", texto, re.I):
            return punto
        if re.search(r"\bpor\s+la\s+izquierda\b", texto, re.I):
            return punto + "-"
        if re.search(r"\bpor\s+la\s+derecha\b", texto, re.I):
            return punto + "+"
    return ""

def _contenido_matematico(ctx: ContextoTurno) -> bool:
    if ctx.expresiones and not ctx.expresiones_heredadas:
        return True
    if ctx.ejercicio_activo and re.search(
        r"\b(?:resultado|me\s+da|me\s+dio|me\s+sale|obtengo|me\s+queda|no\s+existe|diverge)\b",
        ctx.texto_estudiante, re.IGNORECASE,
    ):

        return True
    return bool(hallar_matematica(ctx.texto_estudiante))

def _respuesta_breve_al_ejercicio(texto: str) -> bool:
    from dominio.filtros.intento import propuesta_en_el_turno

    propuesta = propuesta_en_el_turno(texto)
    if not propuesta:
        return False
    escrito = normalizar_frase_matematica(texto.strip().strip("$"))
    propuesto = normalizar_frase_matematica(propuesta)
    return re.sub(r"\s+", "", escrito).replace(",", ".") == re.sub(r"\s+", "", propuesto).replace(",", ".")

class FiltroIntencion(Filtro):

    nombre = "clasificación de intención"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        from dominio.pedagogia.confirmacion import confirma_oferta

        con_matematica = _contenido_matematico(ctx)
        intencion = clasificar(ctx.texto_estudiante, con_matematica)
        from dominio.filtros.intento import anuncia_resultado

        es_enunciado = (extraer_ejercicio_explicito(ctx.texto_estudiante) is not None
                        and not anuncia_resultado(ctx.texto_estudiante))
        if intencion.clase == INTENTO_RESOLUCION and es_enunciado:
            intencion = replace(intencion, clase=PRACTICA_GUIADA, propone_solucion=False,
                                motivo="presenta el ejercicio; no afirma una respuesta propia")
        confirmada = confirma_oferta(ctx.texto_estudiante, ctx.historial_reciente)
        intencion = replace(intencion, confirma_ayuda=confirmada)
        if confirmada:
            intencion = replace(intencion, clase=PETICION_SOLUCION, propone_solucion=False)
        if ctx.señales is not None:
            ctx = replace(ctx, señales=replace(ctx.señales, peticion_confirmada=confirmada))
        if (ctx.ejercicio_activo and not es_enunciado
                and intencion.clase in (AMBIGUA, PETICION_SOLUCION)
                and _respuesta_breve_al_ejercicio(ctx.texto_estudiante)):
            intencion = replace(
                intencion, clase=INTENTO_RESOLUCION, origen=ORIGEN_REGLA,
                motivo="una respuesta matemática breve al ejercicio activo",
                propone_solucion=True,
            )
        from dominio.filtros.intento import niega_resultado

        if (ctx.ejercicio_activo
                and intencion.clase in (AMBIGUA, PETICION_SOLUCION, CONSULTA_CONCEPTUAL, EXPLICACION_DIRECTA, PRACTICA_GUIADA)
                and anuncia_resultado(ctx.texto_estudiante)
                and not niega_resultado(ctx.texto_estudiante)):

            intencion = replace(
                intencion, clase=INTENTO_RESOLUCION, origen=ORIGEN_REGLA,
                motivo="propone un resultado para el ejercicio activo",
                propone_solucion=True,
            )

        limite = _intento_de_limite(ctx.texto_estudiante)

        if (
            limite is None
            and ctx.expresiones_heredadas
            and ctx.expresion_previa
            and intencion.estrategia_solicitada == "cambio_de_representacion"
        ):
            limite = _intento_de_limite(ctx.expresion_previa)
        if limite is None and ctx.ejercicio_activo and ctx.ejercicio_activo.get("tipo") == "limite":
            activo = ctx.ejercicio_activo
            limite = (activo["expresion"], activo["destino"], activo["variable"])
        es_limite = limite is not None
        limite_expresion, limite_destino, limite_variable = limite if limite is not None else ("", "", "x")

        if _intento_de_limite(ctx.texto_estudiante) is not None and intencion.clase == AMBIGUA:
            intencion = replace(
                intencion,
                clase=PETICION_SOLUCION,
                origen=ORIGEN_REGLA,
                motivo="pide un límite: es una petición de cálculo (PM-B24)",
                propone_solucion=False,
            )

        meta = {
            "clase": intencion.clase,
            "origen": intencion.origen,
            "familia": intencion.familia,
            "contenido_matematico": con_matematica,
            "es_limite": es_limite,

            "intencion": intencion.como_dict(),
        }
        if es_limite:
            meta["limite_expresion"] = limite_expresion
            meta["limite_destino"] = limite_destino
            meta["limite_variable"] = limite_variable

        return replace(
            ctx,
            intencion=intencion.clase,
            intencion_origen=intencion.origen,
            intencion_detalle=intencion,
            es_limite=es_limite,
            limite_expresion=limite_expresion,
            limite_destino=limite_destino,
            limite_variable=limite_variable,
        ), meta
