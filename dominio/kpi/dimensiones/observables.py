"""Medidas propias de interacción: contratos nuevos, no escalas psicológicas.

Versionadas y recalculables sobre evidencia elegible de límites y derivadas.
Las definiciones anteriores conservan sus códigos, fórmulas e instrumentos.
"""
from dominio.kpi.contratos import DefinicionKPI, Dimension, Instrumento, MadurezMetodologica, Unidad
from dominio.modelo.senales_interaccion import VERSION

PREFIJO = "conductual.observable_"


def _definir(clave, nombre, criterio, denominador="mensajes analizables", *, matematica=False):
    codigo = PREFIJO + clave
    fuentes = ("historial_turno", "perfil_afectivo", "clase_matricula_historial")
    if matematica:
        fuentes = (*fuentes, "registro_turno")
    return DefinicionKPI(
        codigo=codigo, nombre=nombre, dimension=Dimension.CONDUCTUAL,
        definicion_operacional=f"{criterio}, dividido por {denominador}.",
        unidad=Unidad.PROPORCION, numerador=criterio, denominador=denominador,
        poblacion_elegible="Estudiantes adultos con habilitación conductual vigente, matrícula histórica, turno educativo completo y productor conductual histórico.",
        fuentes=fuentes, muestra_minima=5,
        madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
        limitaciones=("Medida observable del diálogo; no atribuye rasgos, estados internos ni aprendizaje.",
                      "Se relee evidencia histórica con el banco actual. Las reglas omiten lenguaje implícito y pueden confundir expresiones ambiguas.",
                      "Sólo incluye el alcance autorizado y los datos efectivamente registrados; no rellena evidencia ausente."),
        instrumento=Instrumento(nombre="Observables propios del diálogo", version=VERSION,
                               constructo=nombre, escala="proporción de 0 a 1",
                               regla_de_puntuacion="p = casos observados / oportunidades elegibles",
                               minimo_de_observaciones=5),
    )


CATALOGO = (
    _definir("ayuda", "Solicitudes de ayuda reconocidas", "mensajes con solicitud reconocida de explicación, guía, comprobación u otra ayuda"),
    _definir("dificultad", "Dificultad expresada para continuar", "mensajes con dificultad expresada reconocida, como no saber, no entender o perder el hilo"),
    _definir("reticencia", "Reticencia expresada a pedir ayuda", "mensajes con una coincidencia FAH del detector"),
    _definir("aplazamiento", "Aplazamiento o renuncia expresados", "mensajes que expresan dejar el ejercicio o no querer continuar"),
    _definir("reconocimiento_error", "Reconocimiento explícito de un error", "mensajes que reconocen un resultado o procedimiento errado, o declaran una corrección"),
    _definir("preferencia", "Formato de ayuda más solicitado", "mensajes que piden el formato modal", "mensajes con al menos un formato de ayuda solicitado; se conservan empates y solapamientos"),
    _definir("reintento", "Nuevo intento después de un error", "episodios incorrectos con nuevo intento verificable en el mismo problema", "episodios incorrectos con 24 horas completas de seguimiento dentro del periodo", matematica=True),
    _definir("recuperacion", "Resultado correcto después de un error", "nuevos intentos correctos tras uno incorrecto en el mismo hilo y problema", "nuevos intentos verificables tras uno incorrecto", matematica=True),
    _definir("error_verificado", "Resultados incorrectos comprobados", "intentos cuyo resultado fue comprobado como incorrecto por el motor matemático", "intentos con resultado y veredicto matemático comprobable", matematica=True),
    _definir("conceptos_candidatos", "Afirmaciones conceptuales para revisar", "mensajes que afirman una de las relaciones erróneas tipificadas por el banco propio"),
)

CAMBIO = DefinicionKPI(
    codigo=PREFIJO + "cambio_ayuda", nombre="Cambio de solicitudes de ayuda entre dos ventanas",
    dimension=Dimension.CONDUCTUAL, unidad=Unidad.PUNTUACION,
    definicion_operacional="Mediana de diferencias individuales en puntos porcentuales de solicitudes de ayuda entre las dos mitades temporales del periodo, con cinco mensajes por persona en cada mitad.",
    numerador="diferencia individual: 100 × (proporción en segunda mitad − proporción en primera mitad)",
    denominador="personas con al menos cinco mensajes analizables en cada mitad",
    poblacion_elegible=CATALOGO[0].poblacion_elegible,
    fuentes=CATALOGO[0].fuentes, muestra_minima=5,
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    limitaciones=("Describe cambios en el lenguaje registrado, no mejoras, deterioro ni efecto causal del tutor.",
                  "Las mitades del periodo pueden contener tareas y cargas distintas. Se informa cuántas personas quedan sin par.",
                  "Cambiar periodo o versión del detector cambia el contraste; no es un pretest/postest."),
    instrumento=Instrumento(nombre="Observables propios · contraste pareado", version=VERSION,
                           constructo="cambio de solicitudes de ayuda registradas", escala="−100 a 100 puntos porcentuales",
                           regla_de_puntuacion="mediana(100 × (p_segunda − p_primera))",
                           minimo_de_observaciones=5),
)
CATALOGO = (*CATALOGO, CAMBIO)
CODIGOS = frozenset(d.codigo for d in CATALOGO)
