"""
patrones.py — El banco de patrones léxico-sintácticos (`DD-07`, `PM-B10`)
=============================================================================

`DD-07` decide, literalmente: **«se reorientan los patrones existentes de la
iteración 0 y se completan con los indicadores del Eje A que no queden
cubiertos»**. Este módulo es esa reorientación — no una reescritura desde
cero, que `DD-07` consideró y descartó por perder trazabilidad al corpus de
hallazgos, ni un banco mínimo, que desperdiciaría la única oportunidad de
recoger datos reales del piloto con buena cobertura.

De dónde sale cada bloque
------------------------------
`Pre-Arquitectura-Empirica/03-Prototipo-Codigo/indicators/rules.py` —marcado
🔧 por `06-Guia-de-Reutilizacion.md` §3.1— tenía doce patrones de ansiedad con
peso. **Se conservan literalmente para `PS-Anx`**: son evidencia léxica de un
estado de ansiedad EN EL MOMENTO, que es justo lo que `PS-Anx` mide (`ADR-003`
§6.2 nivel 1). Tres de esos doce —los que expresan una creencia de capacidad,
no un estado puntual— se reorientan a `autoeficacia`: *"no sirvo para
esto/nada"*, *"nunca voy a poder"* y *"siempre me equivoco"* no describen
ansiedad sino una **creencia sobre uno mismo**, que es lo que `autoeficacia`
mide y `PS-Anx` no.

`FAH` no tenía patrones en la iteración 0 —el prototipo no distinguía miedo a
pedir ayuda de ansiedad general—, así que sus patrones son **nuevos**, pero no
inventados sin trazo: cubren cuatro de las siete familias que `DD-07` nombra
del Eje A —autodescalificación, disculpas anticipatorias, evitación de ayuda,
comparación social ascendente—, que son precisamente las que se expresan en
el texto de un turno.

Qué familias de `DD-07` NO están cubiertas, y por qué
-----------------------------------------------------------
*Latencia pre-inicio* y *abandono repetido* no son léxicas: son patrones de
**tiempo entre turnos**, que este filtro no puede ver porque solo recibe el
texto de uno. Necesitan que el adaptador de entrada mida y aporte esa señal
—la misma frontera que `dominio/arbitraje/divulgacion.py` ya declara para
`intentos_en_el_problema`—, y no existe todavía.

*Densidad emocional negativa* pide una técnica distinta —proporción de léxico
afectivo sobre el texto, no presencia de un patrón— que un banco de regex con
peso no está pensado para dar bien; forzarla aquí produciría un número sin el
respaldo que el resto de este módulo sí tiene. Queda declarada, no resuelta.

`N3`, la regla del máximo, vive en `extraer()`
----------------------------------------------------
`ADR-003` N3: cuando varias señales del mismo sub-componente concurren en un
turno, `obs_t = max(sᵢ)`, no el promedio — la evidencia no se cancela entre
sí. `extraer()` lo aplica dentro de cada sub-componente, nunca entre
sub-componentes distintos (eso violaría `ADR-003` K1).
"""

from __future__ import annotations

import re

# Revisión de cobertura técnica; los pesos siguen siendo provisionales.
VERSION_BANCO = "lexico-conductual.v2"

#: `PS-Anx` — los doce patrones de ansiedad de `indicators/rules.py`,
#: conservados literalmente, menos los tres que se reorientan abajo.
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

#: `autoeficacia` (baja) — reorientados desde `indicators/rules.py`: son
#: creencia de capacidad, no ansiedad puntual.
_PATRONES_AUTOEFICACIA_BAJA: tuple[tuple[re.Pattern, float], ...] = (
    (re.compile(r"no\s+sirvo\s+para\s+(esto|nada|matem[aá]ticas)", re.I), 0.9),
    (re.compile(r"nunca\s+voy\s+a\s+(poder|aprender|entender)", re.I), 0.9),
    (re.compile(r"siempre\s+me\s+equivoco", re.I), 0.8),
    (re.compile(r"me\s+(rindo|doy\s+por\s+vencid[oa])", re.I), 0.85),
    (re.compile(r"esto\s+no\s+es\s+para\s+m[ií]", re.I), 0.8),
    (re.compile(r"soy\s+mal[oa]\s+para\s+(esto|las\s+matem[aá]ticas)", re.I), 0.85),
)

#: `FAH` — nuevos, completando las familias de `DD-07` que el texto de un
#: turno sí puede delatar: autodescalificación, disculpas anticipatorias,
#: evitación de ayuda, comparación social ascendente.
_PATRONES_FAH: tuple[tuple[re.Pattern, float], ...] = (
    # disculpas anticipatorias
    (re.compile(r"perd[oó]n\s+por\s+preguntar", re.I), 0.8),
    (re.compile(r"disculpa\s+si\s+es\s+(una\s+)?pregunta\s+(tonta|obvia|boba)", re.I), 0.85),
    (re.compile(r"seguro\s+es\s+(una\s+)?pregunta\s+(tonta|obvia|boba)", re.I), 0.8),
    (re.compile(r"s[eé]\s+que\s+es\s+algo\s+b[aá]sico\s+pero", re.I), 0.7),
    # evitación de ayuda
    (re.compile(r"no\s+quiero\s+molestar", re.I), 0.8),
    (re.compile(r"no\s+quiero\s+preguntar\s+tanto", re.I), 0.75),
    (re.compile(r"mejor\s+no\s+pregunto", re.I), 0.75),
    (re.compile(r"no\s+me\s+atrevo\s+a\s+preguntar", re.I), 0.85),
    # autodescalificación dirigida a quien pregunta
    (re.compile(r"debo\s+sonar\s+(tont[oa]|ridicul[oa])", re.I), 0.8),
    (re.compile(r"no\s+quiero\s+parecer\s+tont[oa]", re.I), 0.8),
    # comparación social ascendente
    (re.compile(r"(todos|los\s+dem[aá]s)\s+ya\s+(lo\s+)?(entienden|saben|entendieron)", re.I), 0.75),
    (re.compile(r"seguro\s+soy\s+el\s+[uú]nic[oa]\s+que\s+no\s+entiende", re.I), 0.8),
)

#: Los tres sub-componentes de nivel 1, ruta caliente — `ADR-003` §6.5 S1.
BANCO: dict[str, tuple[tuple[re.Pattern, float], ...]] = {
    "PS-Anx": _PATRONES_PS_ANX,
    "FAH": _PATRONES_FAH,
    "autoeficacia": _PATRONES_AUTOEFICACIA_BAJA,
}

_CITAS = re.compile(r'"[^"\n]*"|«[^»\n]*»|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\'[^\'\n]*\'(?!\w)')
_NEGACION_PREVIA = re.compile(r"\b(?:no|nunca|tampoco)(?:\s+\w+){0,3}\s*$", re.I)


def _afirmado(texto: str, inicio: int) -> bool:
    """Descarta negaciones cercanas; no resuelve ironía ni discurso indirecto."""
    prefijo = re.split(r"[.,;!?\n]", texto[:inicio])[-1]
    return _NEGACION_PREVIA.search(prefijo) is None


def extraer(texto: str) -> dict[str, float]:
    """`obs_t` por sub-componente, aplicando `ADR-003` N3 dentro de cada uno.

    Un sub-componente sin ningún patrón que matchee **no aparece en el
    resultado** — no vale `0.0` a propósito: `EstadoAfectivo.actualizar()`
    trata la ausencia de llamada distinto de un `obs_t=0.0` explícito solo en
    su registro de auditoría (`señal`), así que quien llama decide si un
    sub-componente sin evidencia este turno se actualiza igual (para que
    decaiga) o se deja tal cual.
    """
    resultado: dict[str, float] = {}
    # Los ejemplos citados no se atribuyen al hablante. Se preservan posiciones
    # y fronteras para no juntar palabras al retirar una cita.
    texto = _CITAS.sub(lambda m: " " * len(m.group()), texto)
    for subcomponente, patrones in BANCO.items():
        maximo = 0.0
        for patron, peso in patrones:
            if any(_afirmado(texto, m.start()) for m in patron.finditer(texto)):
                maximo = max(maximo, peso)
        if maximo > 0.0:
            resultado[subcomponente] = maximo
    return resultado
