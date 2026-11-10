"""
adopcion.py — Dimensión A del catálogo v1.1: adopción y permanencia
====================================================================

Los siete indicadores que el encargo enumera bajo «A. Adopción y permanencia».
Los siete son calculables hoy: `historial_turno` y `clase_matricula_historial` existen
desde las migraciones 05 y 08, y el contexto de uso de `EQ-031` desde la 17.

Las cuatro palabras que sostienen esta dimensión —turno válido, sesión, regreso
y población elegible— están definidas una sola vez en
`dominio/kpi/definiciones.py`, y aquí se citan.


"""

from __future__ import annotations

from dominio.kpi.contratos import DefinicionKPI, Dimension, Unidad
from dominio.kpi.definiciones import (
    ACTIVIDAD,
    MUESTRA_MINIMA_DISTRIBUCION,
    POBLACION_ELEGIBLE,
    REGRESO,
    SESION,
    TURNO_VALIDO,
)

#: Las tablas de las que sale toda esta dimensión. En una constante porque
#: repetir la tupla en siete entradas la habría dejado divergir.
FUENTES = ("historial_turno", "clase_matricula_historial", "clase")

_LIMITE_UNA_CLASE = (
    "La migración 18 impone una sola matrícula vigente por estudiante, así que "
    "un cambio de clase mueve toda su actividad futura a la nueva cohorte."
)

ACTIVACION = DefinicionKPI(
    codigo="adopcion.activacion",
    nombre="Activación",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        "Proporción de la población elegible que completó al menos un turno "
        f"válido en el periodo. Turno válido: {TURNO_VALIDO}."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes elegibles con al menos un turno válido en el periodo",
    denominador="estudiantes elegibles en el alcance consultado",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    limitaciones=(
        "Mide haber empezado, no haber aprendido.",
        _LIMITE_UNA_CLASE,
    ),
)

ACTIVIDAD_SEMANAL = DefinicionKPI(
    codigo="adopcion.actividad_semanal",
    nombre="Actividad semanal",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        "Estudiantes elegibles distintos con actividad en los siete días "
        "previos al final del periodo consultado, sobre la población elegible. "
        f"Actividad: {ACTIVIDAD}."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes elegibles distintos con actividad en la ventana de 7 días",
    denominador="estudiantes elegibles en el alcance consultado",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    limitaciones=(
        "La ventana es la última del periodo, no un promedio de todas las "
        "semanas que el periodo abarca.",
    ),
)

RETORNO_7D = DefinicionKPI(
    codigo="adopcion.retorno_7d",
    nombre="Retorno a 7 días",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        f"Proporción de estudiantes que regresaron dentro de 7 días. {REGRESO}. "
        f"Sesión: {SESION}."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes con una segunda sesión dentro de los 7 días siguientes",
    denominador=(
        "estudiantes cuya primera sesión ocurrió dentro del periodo y al menos "
        "7 días antes de su final, de modo que la ventana pudo completarse"
    ),
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    limitaciones=(
        "Quien empezó en los últimos 7 días del periodo no entra en el "
        "denominador: su ventana todavía no terminó, y contarlo como «no "
        "regresó» sería un falso negativo.",
    ),
)

RETORNO_30D = DefinicionKPI(
    codigo="adopcion.retorno_30d",
    nombre="Retorno a 30 días",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        f"Igual que el retorno a 7 días con ventana de 30. {REGRESO}."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes con una segunda sesión dentro de los 30 días siguientes",
    denominador=(
        "estudiantes cuya primera sesión ocurrió dentro del periodo y al menos "
        "30 días antes de su final"
    ),
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    limitaciones=(
        "Un periodo consultado de menos de 30 días deja el denominador vacío y "
        "el indicador responde sin_datos, no cero.",
    ),
)

DIAS_ACTIVOS = DefinicionKPI(
    codigo="adopcion.dias_activos_por_estudiante",
    nombre="Días activos por estudiante",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        "Mediana y percentiles de fechas locales distintas con actividad, por "
        f"estudiante activo. {ACTIVIDAD}."
    ),
    unidad=Unidad.DIAS,
    numerador="fechas locales distintas con actividad, por estudiante",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible=f"{POBLACION_ELEGIBLE}; sólo los que tuvieron actividad",
    fuentes=FUENTES,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
    limitaciones=(
        "Cuenta días con actividad, no tiempo dedicado: el sistema no mide "
        "duración de sesión.",
        "La fecha se deriva en America/Bogota; una conversación de medianoche "
        "pertenece al día local, no al de UTC.",
    ),
)

PROFUNDIDAD_CONVERSACION = DefinicionKPI(
    codigo="adopcion.profundidad_conversacion",
    nombre="Profundidad de conversación",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        f"Mediana y percentiles de turnos válidos por sesión. Sesión: {SESION}."
    ),
    unidad=Unidad.TURNOS,
    numerador="turnos válidos de cada sesión",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible=f"{POBLACION_ELEGIBLE}; sesiones con al menos un turno válido",
    fuentes=FUENTES,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
    limitaciones=(
        "Una conversación larga no es una conversación mejor; el indicador "
        "describe uso, no calidad pedagógica.",
    ),
)

INTERVALO_ENTRE_SESIONES = DefinicionKPI(
    codigo="adopcion.intervalo_entre_sesiones",
    nombre="Intervalo entre sesiones",
    dimension=Dimension.ADOPCION,
    definicion_operacional=(
        "Mediana y percentiles de horas entre el último turno válido de una "
        "sesión y el primero de la siguiente sesión del mismo estudiante."
    ),
    unidad=Unidad.HORAS,
    numerador="horas entre sesiones consecutivas del mismo estudiante",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible=f"{POBLACION_ELEGIBLE}; estudiantes con dos sesiones o más",
    fuentes=FUENTES,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
    limitaciones=(
        "Sólo se miden intervalos cuyas dos sesiones caen dentro del periodo: "
        "el hueco entre el periodo anterior y éste no se cuenta.",
    ),
)

CATALOGO = (
    ACTIVACION,
    ACTIVIDAD_SEMANAL,
    RETORNO_7D,
    RETORNO_30D,
    DIAS_ACTIVOS,
    PROFUNDIDAD_CONVERSACION,
    INTERVALO_ENTRE_SESIONES,
)
