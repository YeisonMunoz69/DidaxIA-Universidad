from __future__ import annotations

import re
from dataclasses import replace

from dominio.arbitraje.divulgacion import ALCANCE_ANALOGO
from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia import estrategias as E
from dominio.pedagogia.andamiaje import Andamiaje, elegir
from dominio.pedagogia.politica import DecisionPedagogica
from dominio.puertos.plantillas import PuertoPlantillas


_TOPE_DE_PREGUNTAS = 6


_COMUN = (
    "No presentes ningún resultado matemático como comprobado: el sistema lo "
    "verifica por separado, después de tu respuesta. No inventes fuentes ni "
    "referencias que no estén en el contexto. Respondes en español y le hablas "
    "al estudiante de tú."
)


_ROL_DE_LA_ESTRATEGIA = {
    E.RESPUESTA_FACTUAL_BREVE: (
        "Eres un tutor de cálculo diferencial. Contesta **en una o dos frases** "
        "lo concreto que te preguntó y para ahí. No abras una explicación larga "
        "ni le devuelvas una pregunta."
    ),
    E.EXPLICACION_TEORICA_DIRECTA: (
        "Eres un tutor de cálculo diferencial. **Explícalo directamente**, de "
        "forma ordenada: qué es, por qué es así y cuándo se usa. No le exijas "
        "contestar nada antes de explicar, y no termines interrogándole."
    ),
    E.EJEMPLO_TRABAJADO: (
        "Eres un tutor de cálculo diferencial. Muéstrale **un ejemplo resuelto** "
        "con los pasos y el resultado declarados para su comprobación, no solo "
        "una lista de funciones ni la identificación de sus partes. Di qué "
        "ilustra ese ejemplo. Puedes cerrar invitándole a probar uno "
        "parecido, pero como invitación, no como examen."
    ),
    E.PRACTICA_GUIADA: (
        "Eres un tutor de cálculo diferencial y le acompañas mientras resuelve "
        "**él**. Explica primero una acción concreta del paso en el que está: "
        "qué sustituir, agrupar o derivar y para qué sirve. Después, si ayuda, "
        "haz una pregunta sobre esa única acción. Deja el trabajo principal "
        "en sus manos. No resuelvas todo el ejercicio."
    ),
    E.DIALOGO_SOCRATICO_APOS: (
        "Eres un tutor socrático de cálculo diferencial. Guíale con **una** "
        "pregunta corta sobre un paso concreto que haya escrito. Usa su "
        "ejercicio y palabras sencillas; no pidas explicar varias decisiones. No corrijas: "
        "aquí no hay error que remediar, hay un salto que acompañar."
    ),
    E.SCAFFOLDING_KQ: (
        "Eres un tutor de cálculo diferencial. **Señala un trozo concreto de lo "
        "que el estudiante escribió** y pídele que justifique ese paso. Una cosa "
        "cada vez; no le corrijas todavía."
    ),
    E.CONFLICTO_CONCEPTUAL: (
        "Eres un tutor de cálculo diferencial. Toma la regla que el estudiante "
        "parece estar usando y **ponla frente a un caso donde no se sostiene**, "
        "para que el choque lo vea él. No le digas que está equivocado."
    ),
    E.DIAGNOSTICO_TWO_TIER: (
        "Eres un tutor de cálculo diferencial. Contesta breve lo que escribió; "
        "el sistema le plantea aparte una pregunta corta de diagnóstico, así que "
        "**no le hagas tú otra pregunta** en esta respuesta."
    ),
    E.PRIMER_PASO_ANTE_BLOQUEO: (
        "Eres un tutor de cálculo diferencial y vas a ofrecer un paso concreto. "
        "Dale **un primer paso concreto** —qué mirar y qué escribir primero— o "
        "una explicación breve que lo desatasque. **No le hagas preguntas "
        "metacognitivas** antes de ayudar. No atribuyas un bloqueo que no expresó."
    ),
    E.DESARROLLO_GUIADO: (
        "Eres un tutor de cálculo diferencial. El desarrollo está autorizado "
        "por sus intentos o porque el motor comprobó que acertó. Explica el "
        "ejercicio paso a paso y resuélvelo con él; reconoce expresamente lo que hizo bien y "
        "no le devuelvas otra pregunta."
    ),
    E.ACLARACION_BREVE: (
        "Eres un tutor de cálculo diferencial y **no sabes todavía qué necesita**. "
        "Haz **una sola** pregunta corta y neutral para averiguarlo. No supongas "
        "qué quería, no empieces una explicación y no propongas un ejercicio."
    ),
}


_FORMATO = (
    "FORMATO DE LA RESPUESTA. Devuelve únicamente un objeto JSON con esta forma "
    "y sin texto alrededor:\n"
    '{"narracion": "...", "afirmaciones": [{"id": "a1", "izquierda": "...", '
    '"relacion": "=", "derecha": "...", "regla": "..."}], '
    '"citadas": [{"id": "c1", "expresion": "..."}], "nivel": 1}\n'
    "\n"
    "Hay TRES clases de contenido y elegir bien es lo que más importa:\n"
    "  · prosa — lo que explicas con palabras;\n"
    "  · **expresión citada** — matemática que solo NOMBRAS, sin decir que sea "
    "igual a nada. Va en «citadas» y se cita con {{c1}};\n"
    "  · **afirmación** — matemática que SÍ afirma una relación. Va en "
    "«afirmaciones» y se cita con {{a1}}.\n"
    "La diferencia no es de forma: es **si afirmas una relación**. «Mira el "
    "seno de equis al cuadrado» es citada; «su derivada es dos equis por "
    "coseno» es afirmación.\n"
    "\n"
    "Reglas, y las cuatro son obligatorias:\n"
    "1. En «narracion» NO puede aparecer ninguna expresión matemática suelta. "
    "Toda matemática va dentro de una afirmación o de una expresión citada, y "
    "la narración la cita por su identificador entre llaves dobles.\n"
    "   En la narración NO escribas: signos = < > ≤ ≥, exponentes con ^, "
    "delimitadores $ de LaTeX, ni fragmentos como f(x) o 2x. **Si necesitas "
    "nombrar una expresión, ponla en «citadas» y cítala** — para eso está.\n"
    "2. Toda referencia {{id}} que escribas debe existir en «afirmaciones», y "
    "toda afirmación que declares debe estar citada en la narración.\n"

    "3. «nivel» vale exactamente NIVEL_PEDIDO, y no lo eliges tú: te lo damos.\n"
    "REGLA_DEL_NIVEL\n"
    "4. «izquierda» y «derecha» son expresiones matemáticas en notación "
    "corriente —`2*x*cos(x^2)`—, no en LaTeX. «regla» nombra la regla que "
    "aplicas, por ejemplo «regla de la cadena».\n"
    "\n"
    "DE_DONDE_SALE_LA_PREGUNTA\n"
    "\n"
    "EJEMPLO\n"
)


_EJEMPLO_DE_NIVEL = {
    1: "Ejemplo de nivel 1, con una expresión citada:\n"
       '{"narracion": "En {{c1}} hay dos cosas multiplicándose. '
       '¿Cuáles dirías que son?", '
       '"afirmaciones": [], "citadas": [{"id": "c1", "expresion": "x*cos(x)"}], '
       '"nivel": 1}',
    2: "Ejemplo de nivel 2, con las dos clases:\n"
       '{"narracion": "En {{c1}} aplica la regla del producto, y queda {{a1}}. '
       '¿Ves de dónde sale cada sumando?", '
       '"afirmaciones": [{"id": "a1", "izquierda": "d/dx (x*cos(x))", '
       '"relacion": "=", "derecha": "cos(x) - x*sen(x)", '
       '"regla": "regla del producto"}], '
       '"citadas": [{"id": "c1", "expresion": "x*cos(x)"}], "nivel": 2}',
    3: "Ejemplo de nivel 3, con el desarrollo paso a paso:\n"
       '{"narracion": "En {{c1}} hay un producto, así que derivas cada factor '
       'y los cruzas: primero {{a1}}, después {{a2}}, y al juntarlos queda '
       '{{a3}}.", '
       '"afirmaciones": ['
       '{"id": "a1", "izquierda": "d/dx (x)", "relacion": "=", '
       '"derecha": "1", "regla": "regla de la potencia"}, '
       '{"id": "a2", "izquierda": "d/dx (cos(x))", "relacion": "=", '
       '"derecha": "-sen(x)", "regla": "derivada del coseno"}, '
       '{"id": "a3", "izquierda": "d/dx (x*cos(x))", "relacion": "=", '
       '"derecha": "cos(x) - x*sen(x)", "regla": "regla del producto"}], '
       '"citadas": [{"id": "c1", "expresion": "x*cos(x)"}], "nivel": 3}',
}


_CON_ANDAMIAJE = "con-andamiaje"
_SIN_ANDAMIAJE = "sin-andamiaje"
_SIN_PREGUNTA = "sin-pregunta"

_DE_DONDE_SALE_LA_PREGUNTA = {
    _CON_ANDAMIAJE: "El ejemplo de abajo enseña la FORMA del JSON y nada más. **La "
                    "pregunta que hagas sale del REPERTORIO de arriba, no de ese "
                    "ejemplo** — copiarlo es responder a otro estudiante.",
    _SIN_ANDAMIAJE: "El ejemplo de abajo enseña la FORMA del JSON y nada más: lo que "
                    "digas sale de lo que el estudiante escribió.",
    _SIN_PREGUNTA: "El ejemplo de abajo enseña la FORMA del JSON y nada más. **En "
                   "este turno no toca preguntar**, sobre la expresión que el "
                   "estudiante trajo y no sobre la del ejemplo.",
}


_ALCANCE_ANALOGO_EN_EL_PROMPT = (
    "ALCANCE DE LO QUE PUEDES REVELAR\n"
    "El estudiante ha pedido que se le explique o que se le ponga un ejemplo, y "
    "eso es lo que autoriza este turno: **la teoría, el procedimiento en "
    "general, o un ejemplo de otro caso**.\n"
    "**No resuelvas el ejercicio que el estudiante está trabajando y no des su "
    "resultado**, ni entero ni como paso final. Si necesitas ilustrar, usa un "
    "caso análogo —otra función, otros números— y dilo: «por ejemplo, con…».\n"
    "No es una restricción de longitud ni de tono: explica todo lo que haga "
    "falta sobre la regla. Es una restricción sobre **qué ejercicio** se "
    "resuelve."
)


_NO_PREGUNTAN = frozenset(
    {
        E.RESPUESTA_FACTUAL_BREVE,
        E.EXPLICACION_TEORICA_DIRECTA,
        E.EJEMPLO_TRABAJADO,
        E.DESARROLLO_GUIADO,
        E.PRIMER_PASO_ANTE_BLOQUEO,
        E.DIAGNOSTICO_TWO_TIER,
    }
)


_REGLA_DE_NIVEL = {
    1: "   El nivel 1 es de sondeo: **no lleva NINGUNA afirmación** y la lista "
       "va vacía. Es `ADR-014` C4 — en este nivel no se declara ningún "
       "resultado, se nombra lo que haga falta con «citadas».",
    2: "   El nivel 2 nombra la regla que aplica y declara sus afirmaciones. "
       "Ya puedes decir qué regla es y declarar el resultado como afirmación.",
    3: "   El nivel 3 muestra el desarrollo: declara cada paso como una "
       "afirmación propia, con su regla.",
}


def _necesidad_corrob(ctx):
    indicaciones = {
        "primer_paso": "Ofrece un primer paso concreto y explica cómo usarlo en el ejercicio activo.",
        "revisar_resultado": "Comunica primero el veredicto disponible del CAS sobre la propuesta. Si no se pudo comprobar, dilo sin declarar acierto o error.",
        "revisar_procedimiento": "Revisa únicamente los pasos que el estudiante escribió; no inventes el procedimiento a partir del resultado.",
        "explicar_razon": "Explica la razón de la regla o transformación que consultó; conocer un resultado no demuestra haberlo calculado.",
        "retomar_ejercicio": "Retoma el ejercicio activo y la consulta pendiente del historial, sin introducir un ejercicio diferente.",
        "resumir": "Resume la explicación previa en pocas frases, conservando el ejercicio y el paso consultado.",
        "ver_ejemplo": "Ofrece un ejemplo relacionado, respetando el alcance de divulgación autorizado.",
        "ver_grafica": "Atiende la petición de gráfica del ejercicio activo en este turno.",
    }
    indicacion = indicaciones.get(ctx.necesidad_pedagogica, "")
    return "AYUDA SOLICITADA CORROBORADA (no es un diagnóstico): " + indicacion if indicacion else ""

class FiltroPrompt(Filtro):

    nombre = "construcción del prompt"
    ruta = "caliente"

    def __init__(self, plantillas: PuertoPlantillas | None = None) -> None:
        self._plantillas = plantillas

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        decision = ctx.decision_pedagogica or DecisionPedagogica()
        estrategia = decision.estrategia

        partes: list[str] = [_rol(estrategia)]

        frase = decision.frase_visible
        if frase:

            partes.append(
                "ABRE TU RESPUESTA con esta idea, dicha con tus palabras y en una "
                f"sola frase: «{frase}»"
            )

        seccion_contexto, fragmentos, sin_fuente = _contexto(ctx)
        if seccion_contexto:
            partes.append(seccion_contexto)

        seccion_orientacion, con_orientacion = _orientacion(ctx)
        if seccion_orientacion:
            partes.append(seccion_orientacion)

        partes.extend(filter(None, (_orientacion_del_intento(ctx),)))
        partes.extend(_peticiones_cotidianas(ctx))
        partes.extend(filter(None, (_necesidad_corrob(ctx),)))

        andamiaje = elegir(
            self._plantillas,
            estrategia=estrategia,
            modificadores=decision.modificadores,
            concepcion=(ctx.diagnostico.concepcion or "") if ctx.diagnostico else "",
            concepciones_candidatas=(
                ctx.precomputo.concepciones_candidatas if ctx.precomputo is not None else ()
            ),
        )
        seccion_andamiaje = _andamiaje(andamiaje)
        if seccion_andamiaje:
            partes.append(seccion_andamiaje)

        seccion_modificadores = _modificadores(decision.modificadores)
        if seccion_modificadores:
            partes.append(seccion_modificadores)

        seccion_historial = _historial(ctx.historial_reciente)
        if seccion_historial:
            partes.append(seccion_historial)

        if (
            ctx.intencion_detalle
            and ctx.intencion_detalle.estrategia_solicitada == E.CAMBIO_DE_REPRESENTACION
        ):
            partes.append(
                "PETICIÓN ACTUAL DE GRÁFICA: atiéndela en ESTE turno. Si el sistema "
                "adjunta una gráfica, explica brevemente qué curva y qué punto de "
                "aproximación se ven; no prometas dibujarla después ni exijas otra "
                "respuesta para mostrarla. Si falta la expresión o no se puede "
                "dibujar, dilo con precisión y pide una sola vez la expresión y "
                "el punto de aproximación necesarios. Una gráfica del límite "
                "muestra la función cerca del punto; no demuestra por sí sola "
                "el valor del límite."
            )

        partes.append(
            "CONTINUIDAD: responde primero a la petición más reciente sobre el "
            "mismo ejercicio. Usa las respuestas que el estudiante ya dio en "
            "el historial; no repitas una pregunta contestada ni cambies de "
            "tema sin que él lo pida."
        )
        partes.append(
            "LENGUAJE Y PREGUNTAS: usa palabras habituales y frases cortas. "
            "Si necesitas un término como composición o conjugado, explica qué "
            "significa con el mismo ejercicio. No imites jerga regional ni atribuyas "
            "emociones que no expresó. Cuando corresponda preguntar, plantea una "
            "sola tarea concreta, fácil de interpretar y responder; no encadenes "
            "qué harías, por qué y cómo lo comprobarías. Ayuda antes de preguntar: "
            "para iniciar, muestra qué sustituir, agrupar o derivar y explica para "
            "qué sirve, respetando el nivel autorizado. No preguntes de nuevo algo "
            "ya contestado. Una petición de explicación o ejemplos se atiende "
            "directamente. Si pide varios ejemplos, entrega la cantidad solicitada "
            "dentro del alcance permitido. Si pregunta solo si recuerdas, resume "
            "lo pertinente sin repetir todos los desarrollos. Si el mensaje incluye "
            "dos consultas, atiende ambas y distingue lo que pudiste comprobar."
        )
        partes.append(
            "EXPRESIONES DEL EJEMPLO: al presentar una función o sus partes, "
            "pon la expresión directamente en citadas. No declares igualdades "
            "con nombres auxiliares como u, v, f(x) o y: una asignación para "
            "nombrar algo no es una equivalencia algebraica verificable sin esa "
            "definición. Por ejemplo, cita sen(x^2) como función y x^2 como parte "
            "interior; declara d/dx (x^2) = 2*x y d/dx (sen(x^2)) = "
            "2*x*cos(x^2) como afirmaciones. Así el verificador puede comprobar "
            "los pasos. No reemplaces un procedimiento solicitado por una "
            "invitación a verlo en el siguiente turno."
        )

        if ctx.alcance_divulgacion == ALCANCE_ANALOGO:
            partes.append(_ALCANCE_ANALOGO_EN_EL_PROMPT)

        partes.append("MENSAJE DEL ESTUDIANTE:\n" + ctx.texto_estudiante.strip())

        nivel = ctx.nivel_divulgacion
        hay_repertorio = andamiaje.principal is not None and andamiaje.principal.utilizable
        if estrategia in _NO_PREGUNTAN:
            de_donde = _SIN_PREGUNTA
        else:
            de_donde = _CON_ANDAMIAJE if hay_repertorio else _SIN_ANDAMIAJE
        partes.append(
            _FORMATO
            .replace("NIVEL_PEDIDO", str(nivel))
            .replace("REGLA_DEL_NIVEL", _REGLA_DE_NIVEL.get(nivel, _REGLA_DE_NIVEL[1]))
            .replace("DE_DONDE_SALE_LA_PREGUNTA", _DE_DONDE_SALE_LA_PREGUNTA[de_donde])
            .replace("EJEMPLO", _EJEMPLO_DE_NIVEL.get(nivel, _EJEMPLO_DE_NIVEL[1]))
        )

        prompt = "\n\n".join(partes)
        meta = {
            "caracteres": len(prompt),
            "estrategia": estrategia,
            "con_contexto": bool(fragmentos),
            "fragmentos_incluidos": fragmentos,
            "con_orientacion": con_orientacion,
            "sin_fuente": sin_fuente,
            "nivel_divulgacion": ctx.nivel_divulgacion,
            "alcance_divulgacion": ctx.alcance_divulgacion,

            "pide_preguntar": estrategia in E.ESTRATEGIAS_SOCRATICAS
            or estrategia == E.ACLARACION_BREVE,
            "orientacion_de_la_pregunta": de_donde,

            "andamiaje": andamiaje.principal.clave if andamiaje.principal else "",
            "andamiaje_motivo": andamiaje.motivo,
            "andamiaje_concepcion": andamiaje.concepcion,
            "andamiaje_tono": [p.clave for p in andamiaje.tono],
            "modificadores": list(decision.modificadores),
            "frase_visible": frase,
        }
        return replace(ctx, prompt=prompt), meta

def _peticiones_cotidianas(ctx: ContextoTurno) -> list[str]:
    texto = ctx.texto_estudiante.lower()
    indicaciones = []
    decision = ctx.decision_pedagogica
    if ctx.intencion == "ambigua" and ctx.ejercicio_activo and decision and decision.estrategia == E.PRIMER_PASO_ANTE_BLOQUEO:
        indicaciones.append("AYUDA ANTE AMBIGÜEDAD: ofrece un paso posible del ejercicio con una explicación corta. No afirmes que el estudiante está bloqueado ni que ya realizó pasos que no constan. Si el referente es incierto, expresa esa condición y pregunta una sola vez al final.")
    if re.search(r"res[uú]m|resume|sintetiz|forma\s+corta|m[aá]s\s+corta", texto):
        indicaciones.append("BREVEDAD PEDIDA: sintetiza en pocas frases el punto pertinente. No vuelvas a desarrollar toda la conversación.")
    if re.search(r"verifica|rectifica|analiza\s+(?:mi|lo\s+que)", texto):
        indicaciones.append("REVISIÓN PEDIDA: revisa primero el procedimiento ya escrito. Identifica el paso comprobable; si falta el procedimiento, pide solo ese dato. No lo sustituyas por otro ejercicio.")
    if re.search(r"perd[ií]\s+el\s+hilo|no\s+te\s+desv[ií]es|no\s+es\s+mi\s+ejercicio", texto):
        indicaciones.append("RETOMAR: identifica el ejercicio y la consulta pendientes del historial y continúa en ese punto. Si hay dos referentes posibles, pide una sola aclaración.")
    if re.search(r"c[oó]mo\s+(?:empiezo|continuar|seguir)|estoy\s+perdid|bloqu(?:ie|e[eé])", texto):
        indicaciones.append("CONTINUACIÓN PEDIDA: aporta un primer paso concreto y explica por qué sirve. No exijas responder una pregunta antes de ayudar. Puedes cerrar con una sola pregunta de continuación si no pidió menos preguntas.")
    return indicaciones

def _rol(estrategia: str) -> str:
    cabecera = _ROL_DE_LA_ESTRATEGIA.get(estrategia, _ROL_DE_LA_ESTRATEGIA[E.ACLARACION_BREVE])
    return cabecera + "\n" + _COMUN

def _contexto(ctx: ContextoTurno) -> tuple[str, int, bool]:
    recuperacion = ctx.recuperacion
    sin_fuente = bool(recuperacion.sin_fuente) if recuperacion is not None else False

    if recuperacion is None or not recuperacion.utilizable:
        nota = (
            "(Sin fuente recuperada para este turno: no dispones de material del "
            "corpus. Sé prudente y no afirmes lo que no puedas fundamentar.)"
        )
        return nota, 0, sin_fuente

    lineas = ["CONTEXTO (fragmentos del corpus; úsalos si son pertinentes):"]
    for f in recuperacion.fragmentos:
        lineas.append(f"--- {f.identificador} · {_procedencia(f)} ---")
        lineas.append(f.texto.strip())
    return "\n".join(lineas), len(recuperacion.fragmentos), sin_fuente

def _andamiaje(andamiaje: Andamiaje) -> str:
    if not andamiaje.utilizable:
        return ""

    hay_principal = andamiaje.principal is not None and andamiaje.principal.utilizable

    lineas = [
        "REPERTORIO. **Tu pregunta sale de aquí.** Escoge UNA de estas y "
        "constrúyela alrededor de lo que el estudiante escribió; adáptala a su "
        "expresión, no la copies literal. No inventes una pregunta genérica "
        "propia habiendo repertorio:"
        if hay_principal
        else "TONO DE LA RESPUESTA. Esto NO cambia lo que respondes —el formato "
        "de abajo manda— sino CÓMO lo dices. Acompaña la respuesta con este "
        "cuidado, sin sustituirla por una pregunta:"
    ]

    if hay_principal:
        lineas.append(f"— {andamiaje.principal.titulo} —")
        lineas += [f"  · {p}" for p in andamiaje.principal.preguntas[:_TOPE_DE_PREGUNTAS]]

    for plantilla in andamiaje.tono:
        lineas.append(f"— {plantilla.titulo} —")
        lineas += [f"  · {p}" for p in plantilla.preguntas[:_TOPE_DE_PREGUNTAS]]

    if hay_principal:
        lineas.append(
            "Lo que va entre ‹› es una RANURA: rellénala con lo que el estudiante "
            "escribió o con un caso de contraste, NUNCA con el resultado."
        )
    lineas.append(
        "No afirmes que el estudiante hizo algo que no se ve en su mensaje: "
        "nombrar una capacidad que no demostró enseña que el sistema no mira."
    )
    return "\n".join(lineas)

def _modificadores(modificadores: tuple[str, ...]) -> str:
    if not modificadores:
        return ""
    lineas = ["CÓMO LO DICES. No cambia qué respondes, sólo la forma:"]
    for modificador in modificadores:
        texto = E.COMO_SE_DICE.get(modificador)
        if texto:
            lineas.append(f"  · {texto}")
    if len(lineas) == 1:
        return ""
    return "\n".join(lineas)

def _procedencia(fragmento) -> str:
    p = fragmento.procedencia
    if p.pagina_hasta is not None:
        return f"{p.obra} p.{p.pagina}-{p.pagina_hasta}"
    return f"{p.obra} p.{p.pagina}"

def _orientacion(ctx: ContextoTurno) -> tuple[str, bool]:
    if ctx.precomputo is None or not ctx.precomputo.ok:
        return "", False

    truncado = ctx.precomputo.truncado()
    lineas = []
    if truncado.regla_critica:
        lineas.append(f"- Regla crítica: {truncado.regla_critica}")
    if truncado.concepciones_candidatas:
        lineas.append(
            "- Posibles concepciones erróneas a vigilar: "
            + ", ".join(truncado.concepciones_candidatas)
        )
    if not lineas:
        return "", False

    cabecera = (
        "ORIENTACIÓN PRIVADA (no la reveles al estudiante; úsala solo para "
        "escoger qué decir):"
    )
    return cabecera + "\n" + "\n".join(lineas), True

def _orientacion_del_intento(ctx: ContextoTurno) -> str:
    if ctx.retroalimentacion_del_intento is not None:
        import json

        base = ctx.retroalimentacion_del_intento
        objeto = {"narracion": base.narracion, "nivel": 2,
                  "afirmaciones": [{"id": a.identificador, "izquierda": a.izquierda,
                                     "relacion": a.relacion, "derecha": a.derecha,
                                     "regla": a.regla_declarada} for a in base.afirmaciones],
                  "citadas": [{"id": c.identificador, "expresion": c.expresion} for c in base.citadas]}
        return (
            "RETROALIMENTACIÓN OBLIGATORIA ANTES DE CUALQUIER SONDEO: el CAS comprobó una propuesta concreta "
            "con el alcance indicado en la base. Un acierto parcial no cierra el ejercicio completo. "
            "Tu narración debe empezar copiando literalmente la narracion de esta base. Conserva sus "
            "afirmaciones y citadas con sus identificadores. Puedes añadir una explicación breve de la regla "
            "referida al ejercicio activo, declarando toda matemática adicional en afirmaciones. "
            "No hagas preguntas. No inventes pasos que el estudiante no escribió ni atribuyas emociones "
            "o concepciones. No despliegues la solución completa. El nivel es exactamente 2. "
            "Esta instrucción prevalece sobre los modificadores que pidan preguntas de autorregulación.\n"
            + json.dumps(objeto, ensure_ascii=False)
        )
    if ctx.resultado_verificado and ctx.precomputo and ctx.precomputo.ok:
        activo = ctx.ejercicio_activo or {}
        pasos = [p for p in ctx.precomputo.pasos if p.tipo not in ("inicio", "verificacion")]
        return (
            "CIERRE DE UN ACIERTO COMPROBADO: el CAS verificó la respuesta "
            f"del estudiante ({ctx.resultado_verificado}) para el ejercicio "
            f"{activo.get('tipo', '')} de {activo.get('expresion', '')}. "
            "Confirma que acertó. Explica en orden los pasos relevantes del "
            "motor, incluida la regla o transformación y el resultado. "
            "No hagas otra pregunta. Declara cada igualdad que muestres en "
            "'afirmaciones' para que el verificador la revise. No reproduzcas "
            "pasos que no se sostengan matemáticamente ni presupongas que "
            "el valor de una función en el punto coincide con su límite.\n"
            "PASOS DEL MOTOR (insumo privado; selecciona los pertinentes):\n"
            + "\n".join(f"- {p.regla}: {p.latex}" for p in pasos[:10])
        )
    if ctx.transformacion_verificada:
        return (
            "TRANSFORMACIÓN COMPROBADA: el CAS confirmó que la expresión "
            f"{ctx.transformacion_verificada} es equivalente a la original "
            "donde ambas están definidas. Reconoce que esta simplificación "
            "es correcta; aún falta hallar el valor del límite. No sugieras "
            "que está equivocada ni repitas una comprobación ya realizada."
        )
    return ""

def _historial(historial: tuple[dict, ...]) -> str:
    if not historial:
        return ""
    lineas = [
        "HISTORIAL DE LA CONVERSACIÓN PREVIA (contexto de los turnos previos; "
        "mantén la coherencia pedagógica con lo conversado):"
    ]
    for h in historial[-6:]:
        est = str(h.get("estudiante", "")).strip()
        tut = str(h.get("tutor", "")).strip()
        if est:
            lineas.append(f"Estudiante: {est}")
        if tut:
            lineas.append(f"Tutor: {tut}")
    if len(lineas) <= 1:
        return ""
    return "\n".join(lineas)
