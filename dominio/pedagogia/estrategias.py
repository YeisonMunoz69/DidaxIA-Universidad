from __future__ import annotations


RESPUESTA_FACTUAL_BREVE = "respuesta_factual_breve"
EXPLICACION_TEORICA_DIRECTA = "explicacion_teorica_directa"
EJEMPLO_TRABAJADO = "ejemplo_trabajado"
PRACTICA_GUIADA = "practica_guiada"
DIALOGO_SOCRATICO_APOS = "dialogo_socratico_apos"
SCAFFOLDING_KQ = "scaffolding_kq"
CONFLICTO_CONCEPTUAL = "conflicto_conceptual"
DIAGNOSTICO_TWO_TIER = "diagnostico_two_tier"
PRIMER_PASO_ANTE_BLOQUEO = "primer_paso_ante_bloqueo"
DESARROLLO_GUIADO = "desarrollo_guiado"

ACLARACION_BREVE = "aclaracion_breve"

ESTRATEGIAS: tuple[str, ...] = (
    RESPUESTA_FACTUAL_BREVE,
    EXPLICACION_TEORICA_DIRECTA,
    EJEMPLO_TRABAJADO,
    PRACTICA_GUIADA,
    DIALOGO_SOCRATICO_APOS,
    SCAFFOLDING_KQ,
    CONFLICTO_CONCEPTUAL,
    DIAGNOSTICO_TWO_TIER,
    PRIMER_PASO_ANTE_BLOQUEO,
    DESARROLLO_GUIADO,
    ACLARACION_BREVE,
)


QUE_HACE = {
    RESPUESTA_FACTUAL_BREVE: (
        "responde el hecho concreto que preguntó, en una o dos frases, sin abrir "
        "una explicación larga ni una cadena de preguntas"
    ),
    EXPLICACION_TEORICA_DIRECTA: (
        "explica el concepto o el procedimiento de forma estructurada, sin exigirle "
        "que conteste nada antes"
    ),
    EJEMPLO_TRABAJADO: (
        "muestra un ejemplo resuelto **diciendo qué ilustra**, y termina con una "
        "invitación opcional a probarlo, nunca con un interrogatorio"
    ),
    PRACTICA_GUIADA: (
        "acompaña mientras resuelve él: el trabajo principal se queda en el "
        "estudiante y el tutor sostiene el paso en el que está"
    ),
    DIALOGO_SOCRATICO_APOS: (
        "acompaña una transición de nivel con preguntas, sin corregir: es para "
        "cuando no hay error que remediar sino un salto que dar"
    ),
    SCAFFOLDING_KQ: (
        "los cinco pasos de señalar, justificar, contrastar, revisar y confirmar, "
        "sobre algo que el estudiante YA escribió"
    ),
    CONFLICTO_CONCEPTUAL: (
        "pone la regla que el estudiante está usando frente a un caso donde no se "
        "sostiene, para que el choque lo produzca él"
    ),
    DIAGNOSTICO_TWO_TIER: (
        "plantea el ítem de dos niveles —resultado primero, razón después— junto a "
        "la respuesta del turno, nunca en su lugar"
    ),
    PRIMER_PASO_ANTE_BLOQUEO: (
        "da un primer paso concreto o una explicación breve para desatascar, sin "
        "encadenar preguntas metacognitivas"
    ),
    DESARROLLO_GUIADO: (
        "muestra el desarrollo paso a paso, declarando cada paso con su regla"
    ),
    ACLARACION_BREVE: (
        "hace UNA sola pregunta corta y neutral para saber qué necesita, sin "
        "suponer qué quería ni empezar una explicación"
    ),
}


ESTRATEGIAS_QUE_REVELAN: frozenset[str] = frozenset({DESARROLLO_GUIADO})


ESTRATEGIAS_SOCRATICAS: frozenset[str] = frozenset(
    {DIALOGO_SOCRATICO_APOS, SCAFFOLDING_KQ, CONFLICTO_CONCEPTUAL}
)


TONO_NO_EVALUATIVO = "tono_no_evaluativo"
APOYO_AFECTIVO_NEUTRAL = "apoyo_afectivo_neutral"
AUTORREGULACION = "autorregulacion"
CAMBIO_DE_REPRESENTACION = "cambio_de_representacion"
GRADO_DE_DETALLE = "grado_de_detalle"
MENOS_PREGUNTAS = "densidad_de_preguntas"

MODIFICADORES: tuple[str, ...] = (
    TONO_NO_EVALUATIVO,
    APOYO_AFECTIVO_NEUTRAL,
    AUTORREGULACION,
    CAMBIO_DE_REPRESENTACION,
    GRADO_DE_DETALLE,
    MENOS_PREGUNTAS,
)


COMO_SE_DICE = {
    TONO_NO_EVALUATIVO: (
        "Habla del error como de un paso del trabajo, no como de un fallo suyo. "
        "No califiques, no felicites de más y no dramatices."
    ),
    APOYO_AFECTIVO_NEUTRAL: (
        "Reconoce en una frase corta que el ejercicio cuesta, sin diagnosticar "
        "nada sobre el estudiante y sin alargarte en ello."
    ),
    AUTORREGULACION: (
        "Cierra invitando a que diga qué va a intentar o cómo comprobaría su "
        "resultado. UNA sola invitación, y no la contestes tú."
    ),
    CAMBIO_DE_REPRESENTACION: (
        "Cambia de representación respecto a lo que ya se probó: si se explicó "
        "en símbolos, usa un caso concreto o una descripción; si se usó un "
        "ejemplo, formula la regla. Cuando haya una expresión evaluable, la "
        "aplicación añadirá su gráfica interactiva a este turno: no digas que "
        "no puedes graficarla ni remitas a una herramienta externa."
    ),
    GRADO_DE_DETALLE: (
        "Sé más detallado de lo habitual en los pasos intermedios: nombra lo que "
        "normalmente se da por sabido."
    ),
    MENOS_PREGUNTAS: (
        "**No termines con una pregunta.** El estudiante ha pedido menos "
        "preguntas: explica y deja el turno cerrado."
    ),
}


FRASE_DE_CAMBIO = {
    EXPLICACION_TEORICA_DIRECTA: "Voy a explicarlo directamente y luego, si quieres, lo practicamos.",
    RESPUESTA_FACTUAL_BREVE: "Te lo respondo corto y seguimos.",
    EJEMPLO_TRABAJADO: "Probemos con un ejemplo concreto.",
    PRACTICA_GUIADA: "Vamos paso a paso, y el ejercicio lo llevas tú.",
    PRIMER_PASO_ANTE_BLOQUEO: "Empecemos sólo por el primer paso.",
    DIALOGO_SOCRATICO_APOS: "Vamos a mirarlo con calma, por partes.",
    SCAFFOLDING_KQ: "Volvamos sobre lo que escribiste, un trozo cada vez.",
    CONFLICTO_CONCEPTUAL: "Probemos tu idea en otro caso, a ver qué pasa.",
    DIAGNOSTICO_TWO_TIER: "Te dejo una pregunta corta para ver por dónde va la duda.",
    DESARROLLO_GUIADO: "Te lo desarrollo entero y lo repasamos juntos.",
    ACLARACION_BREVE: "",
}


def frase_visible(estrategia: str) -> str:
    return FRASE_DE_CAMBIO.get(estrategia, "")
