from __future__ import annotations

from dominio.kpi.contratos import (
    Alcance,
    DefinicionKPI,
    Dimension,
    Instrumentacion,
    Unidad,
)
from dominio.kpi.definiciones import MUESTRA_MINIMA_DISTRIBUCION, POBLACION_ELEGIBLE

FUENTES = ("cola_revision", "clase")

_REVISADAS = (
    "elementos de la cola resueltos en el periodo, en estado aprobado, editado "
    "o rechazado"
)

_LIMITE_ATRIBUCION_COLA = (
    "Los elementos anteriores a la migración 19 no llevan estudiante ni "
    "resolución registrada; el resultado los cuenta como faltantes."
)

TIEMPO_DE_ATENCION = DefinicionKPI(
    codigo="supervision.tiempo_de_atencion",
    nombre="Tiempo hasta la decisión",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Mediana y percentil 95 de horas entre la llegada de un elemento a la "
        "cola y la decisión del docente sobre él."
    ),
    unidad=Unidad.HORAS,
    numerador="horas entre cola_revision.recibido y cola_revision.resuelto_en",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible=_REVISADAS,
    fuentes=FUENTES,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
    limitaciones=(
        "Mide hasta la decisión, no hasta la apertura: cuánto tarda un docente "
        "en ver el elemento es otra medida y hoy no tiene emisor.",
        _LIMITE_ATRIBUCION_COLA,
    ),
)

TASA_DE_INTERVENCION = DefinicionKPI(
    codigo="supervision.tasa_de_intervencion",
    nombre="Tasa de intervención",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Proporción de respuestas revisadas que el docente editó o rechazó con "
        "una respuesta corregida, frente al total de revisadas."
    ),
    unidad=Unidad.PROPORCION,
    numerador="elementos resueltos en estado «editado» o «rechazado»",
    denominador=_REVISADAS,
    poblacion_elegible=_REVISADAS,
    fuentes=FUENTES,
    limitaciones=(
        "Rechazar exige aportar una respuesta corregida, así que se cuenta "
        "como intervención y no como descarte.",
        "No se construyen comparaciones entre docentes a partir de este "
        "indicador: mide la respuesta revisada, no a quien la revisó.",
    ),
)

APROBACION_DIRECTA = DefinicionKPI(
    codigo="supervision.aprobacion_directa",
    nombre="Aprobación directa",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Proporción de respuestas revisadas aprobadas sin modificación."
    ),
    unidad=Unidad.PROPORCION,
    numerador="elementos resueltos en estado «aprobado»",
    denominador=_REVISADAS,
    poblacion_elegible=_REVISADAS,
    fuentes=FUENTES,
    limitaciones=("Es el complemento exacto de la tasa de intervención.",),
)

CARGA_PENDIENTE = DefinicionKPI(
    codigo="supervision.carga_pendiente",
    nombre="Carga pendiente",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Elementos de la cola todavía en estado «pendiente» al final del "
        "periodo, con la antigüedad del más viejo como detalle."
    ),
    unidad=Unidad.CONTEO,
    numerador="elementos pendientes al final del periodo",
    denominador="no aplica: es un recuento",
    poblacion_elegible="elementos encolados dentro del alcance consultado",
    fuentes=FUENTES,

    muestra_minima=1,
    limitaciones=(
        "Es una foto del final del periodo, no un promedio: una cola vaciada "
        "ayer y llena hoy da el mismo número que una siempre llena.",
    ),
)

COBERTURA = DefinicionKPI(
    codigo="supervision.cobertura",
    nombre="Cobertura de supervisión",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Proporción de estudiantes activos elegibles que recibieron al menos "
        "una revisión docente resuelta en el periodo."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes con al menos un elemento resuelto en el periodo",
    denominador="estudiantes elegibles con al menos un turno válido en el periodo",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("cola_revision", "historial_turno", "clase_matricula_historial"),
    limitaciones=(
        "Sólo llegan a la cola las excepciones declaradas, así que una "
        "cobertura baja puede significar que casi nada se degradó.",
        _LIMITE_ATRIBUCION_COLA,
    ),
)

REINCIDENCIA_POSTERIOR = DefinicionKPI(
    codigo="supervision.reincidencia_posterior",
    nombre="Reincidencia posterior",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Proporción de aclaraciones docentes tras las cuales la misma "
        "dificultad reaparece en el mismo estudiante."
    ),
    unidad=Unidad.PROPORCION,
    numerador="aclaraciones seguidas por la reaparición de la misma dificultad",
    denominador="aclaraciones docentes emitidas en el periodo",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=(
        "una identidad estable de «la misma dificultad»; aclaracion_docente "
        "guarda el texto y el turno anclado, pero no la concepción que la "
        "motivó, y sin ella «la misma» no se puede comprobar"
    ),
)

ACTUALIZACION_CURRICULAR = DefinicionKPI(
    codigo="supervision.actualizacion_curricular",
    nombre="Actualización del contexto curricular",
    dimension=Dimension.SUPERVISION,
    definicion_operacional=(
        "Proporción de clases activas cuyo contexto curricular está completo "
        "—unidad declarada— y fue actualizado dentro del periodo consultado."
    ),
    unidad=Unidad.PROPORCION,
    numerador=(
        "clases con unidad_curricular no vacía y contexto_actualizado_en "
        "dentro del periodo"
    ),
    denominador="clases activas en el alcance consultado",
    poblacion_elegible="clases del alcance consultado",
    fuentes=("clase",),
    alcances=(Alcance.DOCENTE, Alcance.INSTITUCIONAL),
    limitaciones=(
        "La unidad curricular es texto libre: el indicador comprueba que exista "
        "y esté fresca, no que describa bien el curso.",
        "Sirve también a la dimensión F del encargo, que pide el mismo dato; "
        "no se duplica el código para no crear dos verdades.",
    ),
)

CATALOGO = (
    TIEMPO_DE_ATENCION,
    TASA_DE_INTERVENCION,
    APROBACION_DIRECTA,
    CARGA_PENDIENTE,
    COBERTURA,
    REINCIDENCIA_POSTERIOR,
    ACTUALIZACION_CURRICULAR,
)
