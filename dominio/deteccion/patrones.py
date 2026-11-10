from __future__ import annotations

import re


VERSION_BANCO = "lexico-conductual.v2"


_PATRONES_PS_ANX: tuple[tuple[re.Pattern, float], ...] = (
    (re.compile(r"no\s+(entiendo|comprendo|puedo|logro)\s+nada", re.I), 0.9),
    (re.compile(r"(es|esto\s+es)\s+(demasiado|muy)\s+dif[ií]cil", re.I), 0.8),
    (re.compile(r"me\s+da\s+miedo\s+equivocarme", re.I), 0.8),
    (re.compile(r"seguro\s+que\s+(est[aá]|lo\s+que\s+hice\s+est[aá])\s+mal", re.I), 0.7),
    (re.compile(r"no\s+estoy\s+segur[oa]\s+de\s+nada", re.I), 0.7),
    (re.compile(r"no\s+s[eé]\s+ni\s+por\s+d[oó]nde\s+empezar", re.I), 0.7),
    (re.compile(r"van\s+muchas\s+veces\s+que\s+me\s+sale\s+mal", re.I), 0.7),
    (re.compile(r"me\s+pongo\s+muy\s+nervios[oa]", re.I), 0.7),
    (re.compile(r"me\s+bloqueo", re.I), 0.7),
    (re.compile(r"\bme\s+bloqu(?:e[eé]|ie|i[eé])\b", re.I), 0.7),
    (re.compile(r"\b(?:estoy|me\s+siento|me\s+puse)\s+(?:muy\s+|re\s+)?nervios[oa]\b", re.I), 0.7),
    (re.compile(r"\bme\s+(?:preocupa|asusta)\s+(?:mucho\s+)?(?:equivocarme|cometer\s+(?:un\s+)?error)\b", re.I), 0.8),
    (re.compile(r"\b(?:tengo|me\s+da)\s+miedo\s+(?:de\s+|a\s+)?(?:equivocarme|cometer\s+(?:un\s+)?error)\b", re.I), 0.8),
    (re.compile(r"\b(?:estoy|me\s+siento)\s+(?:muy\s+)?(?:tens[oa]|estresad[oa]|frustrad[oa])\b", re.I), 0.7),
)


_PATRONES_AUTOEFICACIA_BAJA: tuple[tuple[re.Pattern, float], ...] = (
    (re.compile(r"no\s+sirvo\s+para\s+(esto|nada|matem[aá]ticas)", re.I), 0.9),
    (re.compile(r"nunca\s+voy\s+a\s+(poder|aprender|entender)", re.I), 0.9),
    (re.compile(r"siempre\s+me\s+equivoco", re.I), 0.8),
    (re.compile(r"me\s+(rindo|doy\s+por\s+vencid[oa])", re.I), 0.85),
    (re.compile(r"esto\s+no\s+es\s+para\s+m[ií]", re.I), 0.8),
    (re.compile(r"soy\s+mal[oa]\s+para\s+(esto|las\s+matem[aá]ticas)", re.I), 0.85),
)


_PATRONES_FAH: tuple[tuple[re.Pattern, float], ...] = (

    (re.compile(r"perd[oó]n\s+por\s+preguntar", re.I), 0.8),
    (re.compile(r"disculpa\s+si\s+es\s+(una\s+)?pregunta\s+(tonta|obvia|boba)", re.I), 0.85),
    (re.compile(r"seguro\s+es\s+(una\s+)?pregunta\s+(tonta|obvia|boba)", re.I), 0.8),
    (re.compile(r"s[eé]\s+que\s+es\s+algo\s+b[aá]sico\s+pero", re.I), 0.7),

    (re.compile(r"no\s+quiero\s+molestar", re.I), 0.8),
    (re.compile(r"no\s+quiero\s+preguntar\s+tanto", re.I), 0.75),
    (re.compile(r"mejor\s+no\s+pregunto", re.I), 0.75),
    (re.compile(r"no\s+me\s+atrevo\s+a\s+preguntar", re.I), 0.85),

    (re.compile(r"debo\s+sonar\s+(tont[oa]|ridicul[oa])", re.I), 0.8),
    (re.compile(r"no\s+quiero\s+parecer\s+tont[oa]", re.I), 0.8),

    (re.compile(r"(todos|los\s+dem[aá]s)\s+ya\s+(lo\s+)?(entienden|saben|entendieron)", re.I), 0.75),
    (re.compile(r"seguro\s+soy\s+el\s+[uú]nic[oa]\s+que\s+no\s+entiende", re.I), 0.8),
)


BANCO: dict[str, tuple[tuple[re.Pattern, float], ...]] = {
    "PS-Anx": _PATRONES_PS_ANX,
    "FAH": _PATRONES_FAH,
    "autoeficacia": _PATRONES_AUTOEFICACIA_BAJA,
}

_CITAS = re.compile(r'"[^"\n]*"|«[^»\n]*»|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\'[^\'\n]*\'(?!\w)')
_NEGACION_PREVIA = re.compile(r"\b(?:no|nunca|tampoco)(?:\s+\w+){0,3}\s*$", re.I)


def _afirmado(texto: str, inicio: int) -> bool:
    prefijo = re.split(r"[.,;!?\n]", texto[:inicio])[-1]
    return _NEGACION_PREVIA.search(prefijo) is None

def extraer(texto: str) -> dict[str, float]:
    resultado: dict[str, float] = {}

    texto = _CITAS.sub(lambda m: " " * len(m.group()), texto)
    for subcomponente, patrones in BANCO.items():
        maximo = 0.0
        for patron, peso in patrones:
            if any(_afirmado(texto, m.start()) for m in patron.finditer(texto)):
                maximo = max(maximo, peso)
        if maximo > 0.0:
            resultado[subcomponente] = maximo
    return resultado
