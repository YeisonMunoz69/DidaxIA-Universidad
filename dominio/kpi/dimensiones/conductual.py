"""Dimensión conductual del catálogo kpi.v1.5.

Ocho constructos originales siguen sin fuente y tienen puntuadores
prospectivos. Dos originales tienen formulaciones observables más estrechas:
lenguaje de tensión y conversaciones sin retorno observable en siete días.

Se añade continuidad conversacional observable como código independiente,
calculable sobre historial educativo con seguimiento completo de 24 horas.
No sustituye persistencia frente al error, abandono ni un diagnóstico.
La ficha individual añade tres indicadores del anteproyecto y mantiene
indicios léxicos complementarios separados.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.kpi.contratos import (
    DefinicionKPI,
    Dimension,
    Instrumentacion,
    Instrumento,
    MadurezMetodologica,
    Unidad,
)
from dominio.kpi.definiciones import MUESTRA_MINIMA_DISTRIBUCION, POBLACION_ELEGIBLE
from dominio.modelo.indicios_observables import VERSION as VERSION_INDICIOS

#: Lo que le falta a los diez, escrito una vez. Si un día falta otra cosa para
#: uno de ellos, esa entrada dejará de citar esta constante — y eso será visible
#: en el diff, que es justo lo que se quiere.
FALTA_INSTRUMENTO = (
    "un instrumento aprobado por el equipo: constructo, ítems, escala, regla de "
    "puntuación, mínimo de observaciones y versión. La decisión «Valores y "
    "calibración del modelo afectivo/conductual» sigue abierta en DECISIONES.md, "
    "y perfil_afectivo persiste hoy versiones sin calibrar producidas por una "
    "detección léxica parcial"
)

_LIMITE_NO_CLINICO = (
    "Es un indicador de investigación, nunca un diagnóstico clínico ni un "
    "juicio sobre una persona."
)

_LIMITE_AUTOINFORME = (
    "Cuando exista el instrumento, sus resultados dependerán de lo que la "
    "persona informe o de lo que una rúbrica observe, no de una medida directa "
    "del estado interno."
)


def _pendiente(codigo: str, nombre: str, constructo: str) -> DefinicionKPI:
    """Una entrada conductual sin instrumento, con su constructo declarado.

    Una fábrica y no diez bloques repetidos: los diez comparten exactamente lo
    mismo salvo el nombre y el constructo, y escribir diez copias habría dejado
    que una se quedara vieja al cambiar la redacción de `FALTA_INSTRUMENTO`.
    """
    return DefinicionKPI(
        codigo=codigo,
        nombre=nombre,
        dimension=Dimension.CONDUCTUAL,
        definicion_operacional=(
            f"Puntuación de {constructo} en la población elegible, medida con "
            f"un instrumento versionado. Sin instrumento no se calcula."
        ),
        unidad=Unidad.PUNTUACION,
        numerador="suma de puntuaciones válidas del instrumento",
        denominador="observaciones válidas del instrumento",
        poblacion_elegible=POBLACION_ELEGIBLE,
        fuentes=(),
        instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
        falta=FALTA_INSTRUMENTO,
        muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
        limitaciones=(_LIMITE_NO_CLINICO, _LIMITE_AUTOINFORME),
        instrumento=Instrumento(
            constructo=constructo,
            minimo_de_observaciones=MUESTRA_MINIMA_DISTRIBUCION,
            falta=FALTA_INSTRUMENTO,
        ),
    )


ANSIEDAD_MATEMATICA = _pendiente(
    "conductual.ansiedad_matematica", "Ansiedad matemática", "ansiedad matemática"
)
ANSIEDAD_MATEMATICA = replace(
    ANSIEDAD_MATEMATICA,
    nombre="Ansiedad ante la resolución de problemas (PS-Anx) · lenguaje de tensión",
    definicion_operacional="Mensajes educativos analizables con una coincidencia PS-Anx, divididos por mensajes educativos analizables con traza conductual y habilitación vigente.",
    unidad=Unidad.PROPORCION,
    numerador="mensajes con al menos una coincidencia PS-Anx",
    denominador="mensajes analizables con traza y habilitación vigente",
    poblacion_elegible="Mensajes de estudiantes adultos con habilitación conductual vigente, matrícula histórica y turno educativo completo en el periodo.",
    fuentes=("historial_turno", "perfil_afectivo", "clase_matricula_historial"),
    instrumentacion=Instrumentacion.DISPONIBLE,
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    falta="", muestra_minima=5,
    limitaciones=("Frecuencia léxica, no medición clínica de ansiedad matemática; cero coincidencias no prueba ausencia.",
                  "Los mensajes anteriores al productor conductual quedan fuera del denominador."),
    instrumento=Instrumento(
        nombre="Instrumento-Prototipo · lenguaje de tensión",
        version=VERSION_INDICIOS,
        constructo="lenguaje de tensión al resolver, como indicio parcial de ansiedad matemática",
        escala="proporción de mensajes entre 0 y 1",
        regla_de_puntuacion="p_A = m_A / m",
        minimo_de_observaciones=5,
    ),
)
MIEDO_A_PREGUNTAR = _pendiente(
    "conductual.miedo_a_preguntar", "Miedo a preguntar", "inhibición ante la petición de ayuda"
)
EVITACION = _pendiente(
    "conductual.evitacion", "Evitación", "evitación de la tarea matemática"
)
PERSISTENCIA = _pendiente(
    "conductual.persistencia", "Persistencia", "persistencia ante la dificultad"
)
BUSQUEDA_DE_AYUDA = _pendiente(
    "conductual.busqueda_de_ayuda", "Búsqueda de ayuda", "búsqueda instrumental de ayuda"
)
ABANDONO_DE_CONVERSACION = _pendiente(
    "conductual.abandono_de_conversacion",
    "Sin retorno a la conversación (7 días)",
    "ausencia de retorno al mismo hilo durante siete días",
)
ABANDONO_DE_CONVERSACION = replace(
    ABANDONO_DE_CONVERSACION,
    fuentes=("historial_turno", "clase_matricula_historial"),
    instrumentacion=Instrumentacion.DISPONIBLE,
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    muestra_minima=5,
    poblacion_elegible=(
        "Conversaciones educativas completas de estudiantes con matrícula histórica "
        "vigente, cuya primera respuesta del periodo tiene siete días de seguimiento "
        "íntegros antes del corte. Una oportunidad por estudiante e hilo."
    ),
    limitaciones=(
        "Un hilo sin otro turno puede representar tarea concluida, falta de tiempo o problemas de acceso; no demuestra evitación ni abandono intencional.",
        "Cada conversación aporta una oportunidad. Las ventanas truncadas al corte se excluyen y se informan aparte.",
    ),
)
TOLERANCIA_AL_ERROR = _pendiente(
    "conductual.tolerancia_al_error", "Tolerancia al error", "tolerancia al error"
)
RECUPERACION_TRAS_ERROR = _pendiente(
    "conductual.recuperacion_tras_error",
    "Recuperación tras una respuesta incorrecta",
    "recuperación tras una respuesta incorrecta",
)
PREFERENCIA_NIVELES_AYUDA = _pendiente(
    "conductual.preferencia_niveles_ayuda",
    "Preferencia por niveles de ayuda",
    "preferencia declarada por un nivel de ayuda",
)
CAMBIO_LONGITUDINAL_COHORTE = _pendiente(
    "conductual.cambio_longitudinal_cohorte",
    "Cambio longitudinal por cohorte",
    "cambio longitudinal de los constructos anteriores dentro de una cohorte",
)

CATALOGO = (
    ANSIEDAD_MATEMATICA,
    MIEDO_A_PREGUNTAR,
    EVITACION,
    PERSISTENCIA,
    BUSQUEDA_DE_AYUDA,
    ABANDONO_DE_CONVERSACION,
    TOLERANCIA_AL_ERROR,
    RECUPERACION_TRAS_ERROR,
    PREFERENCIA_NIVELES_AYUDA,
    CAMBIO_LONGITUDINAL_COHORTE,
)

# Código nuevo: no sustituye persistencia, evitación ni abandono psicológico.
CONTINUACION_OBSERVABLE = DefinicionKPI(
    codigo="conductual.continuacion_observable",
    nombre="Continuación conversacional observable",
    dimension=Dimension.CONDUCTUAL,
    definicion_operacional=(
        "Conversaciones con otro turno educativo completo iniciado después de la "
        "primera respuesta observada del periodo y dentro de las 24 horas siguientes, "
        "sobre conversaciones con esa ventana íntegra antes del corte."
    ),
    unidad=Unidad.PROPORCION,
    numerador="conversaciones con continuación registrada dentro de 24 horas",
    denominador="conversaciones con 24 horas completas de observación tras su primera respuesta del periodo",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("historial_turno", "clase_matricula_historial"),
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    limitaciones=(
        "Es continuidad observable, no persistencia ante dificultad ni diagnóstico clínico.",
        "Sin continuación puede significar tarea terminada, cierre de clase o fallo de acceso; no abandono.",
        "Ventana preliminar de 24 horas; no incluye el extremo final del periodo ni conversaciones con seguimiento truncado.",
        "Los turnos sin respuesta registrada no cuentan como continuación completa.",
    ),
)
CATALOGO = (*CATALOGO, CONTINUACION_OBSERVABLE)

REITERACION_TRAS_CORRECCION = DefinicionKPI(
    codigo="conductual.reiteracion_tras_correccion",
    nombre="Sesgo de confirmación · reiteración observada",
    dimension=Dimension.CONDUCTUAL,
    definicion_operacional="Nuevos intentos verificables que repiten la misma propuesta incorrecta después de una estrategia correctiva, sobre nuevos intentos verificables tras esa corrección en el mismo hilo y base matemática.",
    unidad=Unidad.PROPORCION,
    numerador="nuevos intentos con la misma propuesta incorrecta normalizada",
    denominador="nuevos intentos verificables tras corrección en el mismo hilo y tarea",
    poblacion_elegible="Turnos educativos completos de estudiantes adultos con habilitación conductual vigente y trazas legibles de verificación y estrategia.",
    fuentes=("registro_turno", "historial_turno", "clase_matricula_historial"),
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    muestra_minima=5,
    limitaciones=("Una propuesta repetida no demuestra el sesgo cognitivo ni intención; dos episodios son sólo una hipótesis para revisar.",
                  "Compara forma textual en la misma tarea, no equivalencia matemática ni problemas análogos distintos.",
                  "Sin nuevo intento verificable después de la corrección no existe oportunidad medible."),
    instrumento=Instrumento(
        nombre="Instrumento-Prototipo · par corrección-reintento",
        version="anteproyecto.prototipo.v1",
        constructo="reiteración observable después de una estrategia correctiva",
        escala="proporción de oportunidades entre 0 y 1",
        regla_de_puntuacion="p_S = r / o",
        minimo_de_observaciones=5,
    ),
)
CATALOGO = (*CATALOGO, REITERACION_TRAS_CORRECCION)
