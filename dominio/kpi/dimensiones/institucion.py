"""
institucion.py — Dimensión F del catálogo v1.1: docentes e institución
=======================================================================

La dimensión que sólo el investigador consulta. Trece indicadores: ocho
calculables hoy, tres que dependen de la telemetría de versiones que esta
entrega instrumenta, uno que espera un segundo cambio de corpus para tener
sentido y **uno que no se calcula por decisión del equipo**.

El indicador que no se calcula, y por qué
--------------------------------------------------
El encargo pide, bajo la letra F, *«uso del espacio Tutor por docentes»*.
`EQ-031` decidió lo contrario en 2026-09-06, y con nombre propio:

    «ese uso queda excluido de matrícula, evaluación estudiantil, vectores
    conductuales o afectivos, inferencias, alertas, supervisión docente, **KPI**,
    conjuntos de investigación y entrenamiento»

Y el propio encargo lo repite en sus límites: *«conversaciones de
tutor_profesional quedan excluidas de KPI, evaluación e investigación»*. Las dos
frases del mismo encargo no pueden cumplirse a la vez, así que el catálogo
declara el indicador con estado `calculo_no_aplicable` y explica la decisión
que lo excluye, en vez de calcularlo en silencio o borrarlo del catálogo como si
nadie lo hubiera pedido. Resolverlo es una decisión del equipo, no de esta
entrega.

Lo que sí queda medido de esa población es la **operación**: la migración 17
separa el contexto de uso en `registro_turno`, y el resumen de operación que ya
existe cuenta registros y latencias por contexto sin atribuir aprendizaje a
nadie. Eso no es un KPI de esta dimensión y no se mezcla aquí.


"""

from __future__ import annotations

from dominio.kpi.contratos import (
    Alcance,
    DefinicionKPI,
    Dimension,
    Instrumentacion,
    Unidad,
)
from dominio.kpi.definiciones import MUESTRA_MINIMA_DISTRIBUCION, POBLACION_ELEGIBLE

#: Toda la dimensión es institucional: un docente no consulta agregados de la
#: institución, y eso se decide en el catálogo antes que en la ruta.
SOLO_INSTITUCIONAL = (Alcance.INSTITUCIONAL,)

USO_TUTOR_POR_DOCENTES = DefinicionKPI(
    codigo="institucion.uso_tutor_por_docentes",
    nombre="Uso del espacio Tutor por docentes",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de docentes que usaron el Tutor en modo profesional "
        "durante el periodo."
    ),
    unidad=Unidad.PROPORCION,
    numerador="docentes con al menos un turno de contexto «consulta_profesional»",
    denominador="docentes con clase activa en el periodo",
    poblacion_elegible="cuentas con función docente vigente",
    fuentes=(),
    instrumentacion=Instrumentacion.EXCLUIDO_POR_DECISION,
    falta=(
        "EQ-031 excluye el uso profesional del Tutor de todo KPI, y el propio "
        "encargo repite esa exclusión entre sus límites. Publicar este "
        "indicador contradiría una decisión vigente; habilitarlo exige una "
        "decisión nueva del equipo, no una consulta SQL"
    ),
    alcances=SOLO_INSTITUCIONAL,
    limitaciones=(
        "La operación de ese contexto —registros y latencias— sí se observa "
        "aparte, sin atribuir aprendizaje ni evaluación a ninguna persona.",
    ),
)

DOCENTES_ACTIVOS = DefinicionKPI(
    codigo="institucion.docentes_activos",
    nombre="Docentes activos por periodo",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Docentes distintos con al menos una clase que registró un turno "
        "válido de alguno de sus estudiantes en el periodo."
    ),
    unidad=Unidad.CONTEO,
    numerador="docentes distintos con actividad estudiantil en sus clases",
    denominador="no aplica: es un recuento",
    poblacion_elegible="docentes creadores de al menos una clase",
    fuentes=("clase", "clase_matricula_historial", "historial_turno"),
    alcances=SOLO_INSTITUCIONAL,
    limitaciones=(
        "Mide actividad de la clase, no del docente: un docente que no entró "
        "cuenta como activo si sus estudiantes usaron el tutor.",
        "No se construye ningún ordenamiento de docentes a partir de esta "
        "cifra ni de ninguna otra de esta dimensión.",
    ),
)

ESTUDIANTES_ACTIVOS_POR_CLASE = DefinicionKPI(
    codigo="institucion.estudiantes_activos_por_clase",
    nombre="Estudiantes activos por clase",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Mediana y percentiles de estudiantes con al menos un turno válido, "
        "por clase con matrículas vigentes."
    ),
    unidad=Unidad.CONTEO,
    numerador="estudiantes activos de cada clase",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("clase", "clase_matricula_historial", "historial_turno"),
    alcances=SOLO_INSTITUCIONAL,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
    limitaciones=(
        "Una comparación entre clases sin considerar su tamaño y su periodo "
        "no es informativa; por eso se publica la distribución y no un orden.",
    ),
)

COBERTURA_POR_FACULTAD = DefinicionKPI(
    codigo="institucion.cobertura_clases_por_facultad",
    nombre="Cobertura de clases por facultad",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de clases cuya facultad se puede determinar a partir de la "
        "facultad declarada por su docente, con el desglose por facultad como "
        "detalle."
    ),
    unidad=Unidad.PROPORCION,
    numerador="clases cuyo docente tiene facultad declarada",
    denominador="clases del periodo",
    poblacion_elegible="clases con matrículas vigentes",
    fuentes=("clase", "persona"),
    alcances=SOLO_INSTITUCIONAL,
    limitaciones=(
        "La clase no tiene facultad propia: se hereda de su docente, y la "
        "migración 22 dejó la facultad vacía en las filas heredadas.",
    ),
)

COBERTURA_POR_PROGRAMA = DefinicionKPI(
    codigo="institucion.cobertura_clases_por_programa",
    nombre="Cobertura por programa",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de estudiantes elegibles con programa declarado, con el "
        "desglose por programa como detalle."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes elegibles con programa no vacío",
    denominador="estudiantes elegibles",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("clase_matricula_historial", "persona"),
    alcances=SOLO_INSTITUCIONAL,
)

PERFILES_ESTUDIANTE_INCOMPLETOS = DefinicionKPI(
    codigo="institucion.perfiles_estudiante_incompletos",
    nombre="Estudiantes sin perfil académico completo",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de estudiantes elegibles a los que les falta facultad, "
        "programa o semestre."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes elegibles con al menos un campo académico vacío",
    denominador="estudiantes elegibles",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("clase_matricula_historial", "persona"),
    alcances=SOLO_INSTITUCIONAL,
    limitaciones=(
        "Señala qué corregir; la corrección la hace una persona autorizada y "
        "queda auditada.",
    ),
)

COMPLETITUD_PERFILES_DOCENTES = DefinicionKPI(
    codigo="institucion.completitud_perfiles_docentes",
    nombre="Completitud de perfiles docentes",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de docentes con nombre y facultad declarados sobre el "
        "total de docentes con clase."
    ),
    unidad=Unidad.PROPORCION,
    numerador="docentes con nombre y facultad no vacíos",
    denominador="docentes creadores de al menos una clase",
    poblacion_elegible="docentes creadores de al menos una clase",
    fuentes=("clase", "persona"),
    alcances=SOLO_INSTITUCIONAL,
)

CLASES_SIN_ACTIVIDAD = DefinicionKPI(
    codigo="institucion.clases_sin_actividad",
    nombre="Clases sin actividad",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de clases con matrículas vigentes que no registraron "
        "ningún turno válido en el periodo."
    ),
    unidad=Unidad.PROPORCION,
    numerador="clases con matrículas y sin turnos válidos en el periodo",
    denominador="clases con al menos una matrícula vigente",
    poblacion_elegible="clases con matrículas vigentes",
    fuentes=("clase", "clase_matricula_historial", "historial_turno"),
    alcances=SOLO_INSTITUCIONAL,
    limitaciones=(
        "Una clase creada dentro del periodo tiene menos oportunidad de "
        "registrar actividad; el indicador no ajusta por eso.",
    ),
)

DISTRIBUCION_TAMANO_DE_CLASE = DefinicionKPI(
    codigo="institucion.distribucion_tamano_de_clase",
    nombre="Distribución de tamaños de clase",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Mediana y percentiles de matrículas vigentes por clase."
    ),
    unidad=Unidad.CONTEO,
    numerador="matrículas vigentes de cada clase",
    denominador="no aplica: es una distribución, no una razón",
    poblacion_elegible="clases con al menos una matrícula vigente",
    fuentes=("clase", "clase_matricula_historial"),
    alcances=SOLO_INSTITUCIONAL,
    muestra_minima=MUESTRA_MINIMA_DISTRIBUCION,
)

MATRICULADOS_SIN_ACTIVAR = DefinicionKPI(
    codigo="institucion.matriculados_sin_activar",
    nombre="Matriculados que no activan el tutor",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Proporción de estudiantes elegibles sin ningún turno válido en el "
        "periodo. Complemento exacto de la activación."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes elegibles sin turnos válidos en el periodo",
    denominador="estudiantes elegibles",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("clase_matricula_historial", "historial_turno"),
    alcances=SOLO_INSTITUCIONAL,
)

_FALTA_HISTORICO_DE_VERSIONES = (
    "historial de versiones observadas; esta entrega instrumenta el evento "
    "«turno.respondido» con la versión de corpus y de modelo realmente usadas, "
    "así que el indicador empieza a acumular desde su despliegue y no puede "
    "reconstruir el pasado, que nunca se registró"
)

VERSIONES_DE_CORPUS = DefinicionKPI(
    codigo="institucion.versiones_de_corpus",
    nombre="Versiones de corpus utilizadas",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Versiones de corpus distintas observadas en las respuestas del "
        "periodo, con su reparto de turnos como detalle."
    ),
    unidad=Unidad.CONTEO,
    numerador="versiones de corpus distintas observadas",
    denominador="no aplica: es un recuento",
    poblacion_elegible="turnos válidos con evento de respuesta registrado",
    fuentes=("evento_telemetria",),
    alcances=SOLO_INSTITUCIONAL,
    depende_de_corpus=True,
    limitaciones=(_FALTA_HISTORICO_DE_VERSIONES,),
)

VERSIONES_DE_MODELO = DefinicionKPI(
    codigo="institucion.versiones_de_modelo",
    nombre="Versiones de modelo utilizadas",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Versiones de modelo distintas que **respondieron de verdad** en el "
        "periodo, leídas de la respuesta del proveedor y no de la "
        "configuración, con su reparto de turnos como detalle."
    ),
    unidad=Unidad.CONTEO,
    numerador="versiones de modelo distintas observadas",
    denominador="no aplica: es un recuento",
    poblacion_elegible="turnos válidos con evento de respuesta registrado",
    fuentes=("evento_telemetria",),
    alcances=SOLO_INSTITUCIONAL,
    depende_de_modelo=True,
    limitaciones=(_FALTA_HISTORICO_DE_VERSIONES,),
)

RECUPERACION_TRAS_CAMBIO_DE_CORPUS = DefinicionKPI(
    codigo="institucion.recuperacion_tras_cambio_de_corpus",
    nombre="Cambio en recuperación tras actualizar el corpus",
    dimension=Dimension.INSTITUCION,
    definicion_operacional=(
        "Cobertura observada bajo la última versión de corpus del periodo, con "
        "la de la versión anterior y su diferencia como detalle. El valor "
        "publicado es la cobertura actual; la comparación va al lado para que "
        "una diferencia no se lea como una cifra absoluta."
    ),
    unidad=Unidad.PROPORCION,
    numerador=(
        "turnos respondidos bajo la última versión de corpus cuya procedencia "
        "no fue «sin-fuente»"
    ),
    denominador="turnos respondidos bajo la última versión de corpus",
    poblacion_elegible="turnos válidos con evento de respuesta registrado",
    fuentes=("evento_telemetria", "historial_material"),
    alcances=SOLO_INSTITUCIONAL,
    depende_de_corpus=True,
    limitaciones=(
        "Compara dos periodos contiguos separados por un cambio de corpus; "
        "describe una diferencia observada y no permite inferir una causa.",
        _FALTA_HISTORICO_DE_VERSIONES,
    ),
)

CATALOGO = (
    USO_TUTOR_POR_DOCENTES,
    DOCENTES_ACTIVOS,
    ESTUDIANTES_ACTIVOS_POR_CLASE,
    COBERTURA_POR_FACULTAD,
    COBERTURA_POR_PROGRAMA,
    PERFILES_ESTUDIANTE_INCOMPLETOS,
    COMPLETITUD_PERFILES_DOCENTES,
    CLASES_SIN_ACTIVIDAD,
    DISTRIBUCION_TAMANO_DE_CLASE,
    MATRICULADOS_SIN_ACTIVAR,
    VERSIONES_DE_CORPUS,
    VERSIONES_DE_MODELO,
    RECUPERACION_TRAS_CAMBIO_DE_CORPUS,
)
