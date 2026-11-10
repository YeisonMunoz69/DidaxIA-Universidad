from dataclasses import asdict, dataclass

VERSION = "anteproyecto.hibrido.experimental.v4"
NOMBRES = {
    "PS-Anx": "Ansiedad ante la resolución de problemas (PS-Anx)",
    "preconcepciones": "Preconcepciones erróneas",
    "confirmacion": "Sesgo de confirmación",
}
ESTADOS = frozenset({"detectado", "no_detectado", "no_concluyente"})
CODIGOS_RECHAZO = {
    'se requieren los tres factores del anteproyecto': 'factores_incompletos',
    'factores repetidos o ausentes': 'factores_repetidos',
    'factor fuera de la rúbrica': 'factor_desconocido',
    'estado u oportunidad inválidos': 'estado_oportunidad_invalida',
    'evidencia conductual no anclada al turno': 'cita_no_literal_o_extensa',
    'motivo conductual inválido': 'motivo_invalido',
    'detección sin oportunidad': 'deteccion_sin_oportunidad',
}
RUBRICA = {
    "version": VERSION,
    'revision_prompt': 'v4.0-turno-actual',
    "alcance": "Indicios observables en el diálogo; no intensidad ni diagnóstico de personas.",
    "PS-Anx": {
        "criterio": "Lenguaje propio de tensión, miedo o preocupación al resolver matemática.",
        "incluir": ["me pone nervioso equivocarme", "me angustia este ejercicio"],
        "excluir": ["no lo sé", "no entendí", "no me preguntes", "el profesor dijo que estaba nervioso"],
        "nota": "Dificultad e incertidumbre sin tensión no bastan. Distingue negaciones, citas y humor ambiguo. Una retractación explícita ('es una broma, estoy tranquilo') no sostiene tensión propia; humor sin aclaración puede ser no_concluyente.",
    },
    "preconcepciones": {
        "criterio": "Afirmación o razón matemática propia que sostiene una relación conceptual errónea.",
        "incluir": ["dividir por cero da cero", "si sale 0/0 el límite no existe",
                    "la derivada del producto es el producto de derivadas"],
        "excluir": ["una respuesta numérica aislada", "una pregunta sobre una regla",
                    "una afirmación citada o refutada", "un error de cálculo sin razón conceptual"],
        "correctas": ["que salga 0/0 no significa que el límite no exista",
                      "una función puede no estar definida en el punto y tener límite",
                      "la derivada del producto necesita sumar dos productos"],
        "nota": "Una afirmación conceptual propia correcta es oportunidad=true, estado=no_detectado. Si no puedes señalar la relación errónea, usa no_concluyente, nunca detectado por mera incompletitud. Es candidata, no concepción estable ni sondeo de dos niveles.",
    },
    "confirmacion": {
        "criterio": "Mantiene la misma respuesta, procedimiento o relación errónea después de una corrección en el mismo problema.",
        "incluir": ["insiste en el mismo procedimiento después de la corrección"],
        "excluir": ["explica de nuevo", "no entendí", "otro problema", "corrige la respuesta", "prueba otra estrategia"],
        "nota": "La oportunidad y la corrección entregada se comprueban con las trazas; no las inventes. Es indicio, no demostración del sesgo.",
    },
}


@dataclass(frozen=True)
class ObservacionConductual:
    factor: str
    estado: str
    evidencia: str
    motivo: str
    oportunidad: bool

    def como_dict(self):
        return asdict(self)

def validar_factores(datos, mensaje):
    if not isinstance(datos, list) or len(datos) != len(NOMBRES):
        raise ValueError("se requieren los tres factores del anteproyecto")
    observaciones = tuple(_validar_uno(d, mensaje) for d in datos)
    if {d.factor for d in observaciones} != set(NOMBRES):
        raise ValueError("factores repetidos o ausentes")
    return observaciones

def _validar_uno(dato, mensaje):
    if not isinstance(dato, dict) or not isinstance(dato.get("factor"), str) or dato["factor"] not in NOMBRES:
        raise ValueError("factor fuera de la rúbrica")
    if not isinstance(dato.get("estado"), str) or dato["estado"] not in ESTADOS or type(dato.get("oportunidad")) is not bool:
        raise ValueError("estado u oportunidad inválidos")
    evidencia, motivo = dato.get("evidencia"), dato.get("motivo")
    if not isinstance(evidencia, str) or not evidencia or len(evidencia) > 240 or evidencia not in mensaje:
        raise ValueError("evidencia conductual no anclada al turno")
    if not isinstance(motivo, str) or not motivo or len(motivo) > 400:
        raise ValueError("motivo conductual inválido")
    if dato["estado"] == "detectado" and not dato["oportunidad"]:
        raise ValueError("detección sin oportunidad")
    return ObservacionConductual(dato["factor"], dato["estado"], evidencia, motivo, dato["oportunidad"])
