"""
aprendizaje.py — Dimensión B del catálogo v1.2: aprendizaje y acompañamiento
=============================================================================

Seis indicadores, y **dos son calculables hoy**. Esta dimensión es la que
más honestidad exige del catálogo, porque es la que más se parece a lo que un
tablero querría enseñar y la que menos evidencia real tiene detrás.

Qué se puede afirmar y qué no
--------------------------------------
`historial_turno.nivel` guarda el nivel de divulgación que el arbitraje emitió
—`sondeo`, `regla`, `desarrollo`, según `dominio/arbitraje/divulgacion.py`— y
eso permite medir **escalamiento de ayuda** sin inventar nada: es un hecho
persistido de lo que el sistema hizo.

La autocorrección sólo se publica como una medida experimental de eventos
explícitos de interfaz: candidato detectado y confirmación del estudiante. No
demuestra por sí sola corrección matemática ni aprendizaje.

Lo demás no. `perfil_conceptual` existe desde la migración 02 y **no tiene
productor**; `cola_revision.concepcion_candidata` admite NULL y hoy nadie la
llena. El encargo lo dice sin rodeos para dos de ellos: *«Resolución y
transferencia necesitan rúbricas o ítems de comprobación. No deduzcas
aprendizaje únicamente del texto libre»*. Se aplica el mismo criterio a los
otros indicadores sin fuente verificable.


"""

from __future__ import annotations

from dominio.kpi.contratos import (
    DefinicionKPI,
    Dimension,
    Instrumentacion,
    Instrumento,
    MadurezMetodologica,
    Unidad,
)
from dominio.kpi.definiciones import POBLACION_ELEGIBLE, TURNO_VALIDO

_NO_HAY_CATALOGO_POR_CLASE = (
    "un catálogo de conceptos declarado por clase o curso y una marca "
    "persistida de qué concepto trabajó cada turno; hoy el contexto curricular "
    "de la migración 20 guarda una unidad en texto libre, que no es una lista "
    "de conceptos, y ningún turno queda ligado a un concepto del banco"
)

COBERTURA_CONCEPTUAL = DefinicionKPI(
    codigo="aprendizaje.cobertura_conceptual",
    nombre="Cobertura conceptual",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Conceptos del catálogo trabajados en el periodo sobre los conceptos "
        "definidos para la clase o el curso."
    ),
    unidad=Unidad.PROPORCION,
    numerador="conceptos distintos trabajados en turnos válidos del periodo",
    denominador="conceptos declarados para la clase o el curso",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=_NO_HAY_CATALOGO_POR_CLASE,
    limitaciones=(
        "Aunque existiera el catálogo, «trabajado» no significa «comprendido».",
    ),
)

ESCALAMIENTO_DE_AYUDA = DefinicionKPI(
    codigo="aprendizaje.escalamiento_de_ayuda",
    nombre="Escalamiento de ayuda",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Proporción de turnos válidos que el arbitraje emitió por encima del "
        "sondeo, es decir con nivel «regla» o «desarrollo». El nivel lo decide "
        "dominio/arbitraje/divulgacion.py y se persiste en historial_turno."
    ),
    unidad=Unidad.PROPORCION,
    numerador="turnos válidos con nivel «regla» o «desarrollo»",
    denominador=f"turnos válidos con nivel registrado. Turno válido: {TURNO_VALIDO}",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("historial_turno", "clase_matricula_historial"),
    limitaciones=(
        "Mide lo que el sistema emitió, no lo que el estudiante necesitaba: un "
        "escalamiento alto puede indicar dificultad o una política del "
        "arbitraje, y el indicador no las distingue.",
        "Los turnos anteriores a la migración 06 no tienen nivel registrado y "
        "quedan fuera del denominador; el resultado los reporta como faltantes.",
    ),
)

AUTOCORRECCION = DefinicionKPI(
    codigo="aprendizaje.autocorreccion",
    nombre="Autocorrección",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Proporción de candidatos de autocorrección detectados por la interfaz "
        "que el estudiante confirma explícitamente en el mismo turno."
    ),
    unidad=Unidad.PROPORCION,
    numerador="candidatos de error con autocorrección confirmada explícitamente",
    denominador="candidatos de error detectados en turnos válidos",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("evento_telemetria", "clase_matricula_historial"),
    instrumentacion=Instrumentacion.DISPONIBLE,
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    limitaciones=(
        "Mide confirmaciones explícitas de la interfaz, no demuestra que la "
        "corrección matemática sea válida ni que haya ocurrido sin ayuda.",
        "Los turnos anteriores al productor de estos eventos quedan fuera del denominador.",
    ),
)

_NO_HAY_DIAGNOSTICO_PERSISTIDO = (
    "un diagnóstico conceptual persistido por turno; perfil_conceptual existe "
    "desde la migración 02 y no tiene productor, y "
    "cola_revision.concepcion_candidata admite NULL y hoy nadie la llena"
)

RECURRENCIA_CONCEPCIONES = DefinicionKPI(
    codigo="aprendizaje.recurrencia_concepciones",
    nombre="Recurrencia de concepciones erróneas",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Proporción de concepciones erróneas detectadas que reaparecen en una "
        "sesión posterior del mismo estudiante."
    ),
    unidad=Unidad.PROPORCION,
    numerador="concepciones que reaparecen en una sesión posterior",
    denominador="concepciones erróneas detectadas en el periodo",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=_NO_HAY_DIAGNOSTICO_PERSISTIDO,
)

RESOLUCION_POSTERIOR = DefinicionKPI(
    codigo="aprendizaje.resolucion_posterior",
    nombre="Resolución posterior",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Proporción de concepciones erróneas que el estudiante responde "
        "después correctamente **mediante un instrumento verificable**, no por "
        "lectura de texto libre."
    ),
    unidad=Unidad.PROPORCION,
    numerador="concepciones resueltas en un ítem de comprobación posterior",
    denominador="concepciones erróneas detectadas con ítem de comprobación aplicado",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=(
        "un banco de ítems de comprobación con su rúbrica, aplicado y "
        "persistido; el encargo prohíbe expresamente deducir aprendizaje del "
        "texto libre, y el sondeo de dos niveles que existe hoy casi nunca se "
        "activa en turnos abiertos"
    ),
    instrumento=Instrumento(
        constructo="resolución de una concepción errónea previamente detectada",
        falta="banco de ítems, rúbrica de corrección y versión aprobada por el equipo",
    ),
)

TRANSFERENCIA_REPRESENTACION = DefinicionKPI(
    codigo="aprendizaje.transferencia_representacion",
    nombre="Transferencia de representación",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional=(
        "Proporción de estudiantes que demuestran pasar entre descripción "
        "verbal, expresión, tabla y gráfica en un ítem de comprobación."
    ),
    unidad=Unidad.PROPORCION,
    numerador="estudiantes con transferencia demostrada en el instrumento",
    denominador="estudiantes a los que se aplicó el instrumento",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=(
        "una rúbrica de registros de Duval con ítems que exijan el cambio de "
        "representación; el corpus etiqueta el registro de cada fragmento, "
        "pero eso describe el material, no lo que el estudiante hizo"
    ),
    instrumento=Instrumento(
        constructo="tránsito entre registros de representación (Duval)",
        falta="ítems, rúbrica, escala y versión aprobada por el equipo",
    ),
)

CATALOGO = (
    COBERTURA_CONCEPTUAL,
    ESCALAMIENTO_DE_AYUDA,
    AUTOCORRECCION,
    RECURRENCIA_CONCEPCIONES,
    RESOLUCION_POSTERIOR,
    TRANSFERENCIA_REPRESENTACION,
)

CONCEPCIONES_DOS_NIVELES = DefinicionKPI(
    codigo="aprendizaje.concepciones_dos_niveles",
    nombre="Preconcepciones erróneas · sondeo de dos niveles",
    dimension=Dimension.APRENDIZAJE,
    definicion_operacional="Sondeos clasificados con M16, M21, M22 o M23 entre sondeos de dos niveles clasificados por el servidor en turnos educativos completos.",
    unidad=Unidad.PROPORCION,
    numerador="sondeos clasificados con una de las cuatro concepciones comprometidas",
    denominador="sondeos de dos niveles clasificados",
    poblacion_elegible="Sondeos de estudiantes adultos con habilitación vigente y traza diagnóstica legible, matrícula histórica y turno completo en el periodo.",
    fuentes=("registro_turno", "historial_turno", "clase_matricula_historial"),
    madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
    muestra_minima=5,
    limitaciones=("Mide respuestas tipificadas en cuatro concepciones; no mide conocimiento global ni aprendizaje.",
                  "Un candidato del motor simbólico sin respuesta de dos niveles no entra como diagnóstico.",
                  "Los sondeos no clasificados no se imputan como ausencia de concepción."),
    instrumento=Instrumento(
        nombre="Instrumento-Prototipo · sondeo de dos niveles",
        version="anteproyecto.prototipo.v1",
        constructo="concepciones M16, M21, M22 y M23 en respuestas clasificadas",
        escala="proporción de sondeos entre 0 y 1",
        regla_de_puntuacion="p_C = (d16 + d21 + d22 + d23) / s",
        minimo_de_observaciones=5,
    ),
)
CATALOGO = (*CATALOGO, CONCEPCIONES_DOS_NIVELES)
