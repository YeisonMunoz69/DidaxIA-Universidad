from __future__ import annotations

from dominio.kpi.contratos import DefinicionKPI, Dimension, Instrumentacion, Unidad
from dominio.kpi.definiciones import POBLACION_ELEGIBLE, TURNO_VALIDO

FUENTES = ("historial_turno", "historial_material", "clase_matricula_historial")

TURNO_ELEGIBLE = (
    f"turno válido con voz del sistema registrada. Turno válido: {TURNO_VALIDO}"
)

COBERTURA = DefinicionKPI(
    codigo="recuperacion.cobertura",
    nombre="Cobertura de recuperación",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de turnos elegibles en los que el recuperador aportó al "
        "menos un fragmento del corpus al contexto de la respuesta."
    ),
    unidad=Unidad.PROPORCION,
    numerador="turnos elegibles con al menos un material de relación «recuperado»",
    denominador=f"turnos elegibles. {TURNO_ELEGIBLE}",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    depende_de_corpus=True,
    limitaciones=(
        "«Recuperado» significa que el fragmento entró al contexto del prompt, "
        "no que la respuesta lo use ni que respalde una frase concreta; la "
        "migración 16 lo declara así y el catálogo no lo sobreinterpreta.",
    ),
)

TASA_SIN_FUENTE = DefinicionKPI(
    codigo="recuperacion.tasa_sin_fuente",
    nombre="Tasa sin fuente",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de turnos elegibles cuya respuesta declaró procedencia "
        "«sin-fuente»."
    ),
    unidad=Unidad.PROPORCION,
    numerador="turnos elegibles con procedencia_origen = 'sin-fuente'",
    denominador=f"turnos elegibles. {TURNO_ELEGIBLE}",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("historial_turno", "clase_matricula_historial"),
    depende_de_corpus=True,
    limitaciones=(
        "No es el complemento exacto de la cobertura: un turno puede recuperar "
        "material y aun así resolverse sin declararlo como fuente.",
    ),
)

DIVERSIDAD_DE_FUENTES = DefinicionKPI(
    codigo="recuperacion.diversidad_de_fuentes",
    nombre="Diversidad de fuentes",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Fragmentos distintos del corpus recuperados en el periodo, con el "
        "recuento de obras distintas como detalle."
    ),
    unidad=Unidad.CONTEO,
    numerador="fragmentos distintos recuperados",
    denominador="no aplica: es un recuento",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    depende_de_corpus=True,
    limitaciones=(
        "Depende del tamaño del corpus indexado: comparar dos periodos con "
        "corpus distintos compara dos cosas.",
    ),
)

CONCENTRACION_DOCUMENTAL = DefinicionKPI(
    codigo="recuperacion.concentracion_documental",
    nombre="Concentración documental",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de las apariciones de material que acumulan los cinco "
        "fragmentos más recuperados del periodo."
    ),
    unidad=Unidad.PROPORCION,
    numerador="apariciones de los cinco fragmentos más recuperados",
    denominador="apariciones totales de material recuperado",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=FUENTES,
    depende_de_corpus=True,
    limitaciones=(
        "Una concentración alta puede describir un curso enfocado en pocos "
        "temas o un índice que devuelve siempre lo mismo; el indicador no las "
        "distingue.",
    ),
)

APERTURA_DE_FUENTES = DefinicionKPI(
    codigo="recuperacion.apertura_de_fuentes",
    nombre="Apertura de fuentes",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de respuestas con material disponible en las que la "
        "persona abrió el panel «Fuentes»."
    ),
    unidad=Unidad.PROPORCION,
    numerador="respuestas con al menos un evento «fuentes.abiertas»",
    denominador="respuestas con material recuperado disponible",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("evento_telemetria", "historial_material"),
    limitaciones=(
        "Abrir el panel no demuestra haber leído la fuente.",
        "La cobertura empieza cuando se publica el productor de interfaz; los "
        "turnos anteriores pueden aportar denominador sin evento observable.",
    ),
)

BLOQUES_VERIFICADOS = DefinicionKPI(
    codigo="recuperacion.bloques_verificados",
    nombre="Bloques verificados",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de bloques verificables emitidos con sello «verificado». "
        "Bloque verificable: los de tipo «notacion», únicos que el emisor puede "
        "sellar como verificados."
    ),
    unidad=Unidad.PROPORCION,
    numerador="bloques de tipo «notacion» con sello «verificado»",
    denominador="bloques de tipo «notacion» emitidos en turnos válidos",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("historial_bloque", "historial_turno", "clase_matricula_historial"),
    limitaciones=(
        "El sello lo decide el emisor cuando el motor simbólico aprobó la "
        "respuesta y el arbitraje pasó del sondeo; una tasa baja puede deberse "
        "a un nivel de divulgación bajo y no a un fallo de verificación.",
    ),
)

PRECISION_AUDITADA = DefinicionKPI(
    codigo="recuperacion.precision_auditada",
    nombre="Precisión de recuperación auditada",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de fragmentos considerados pertinentes en una muestra "
        "revisada por personas."
    ),
    unidad=Unidad.PROPORCION,
    numerador="fragmentos marcados como pertinentes por la persona revisora",
    denominador="fragmentos de la muestra revisada",
    poblacion_elegible="muestra de material recuperado seleccionada para revisión",
    fuentes=(),
    instrumentacion=Instrumentacion.SIN_INSTRUMENTO,
    falta=(
        "un procedimiento de muestreo, una rúbrica de pertinencia y una "
        "superficie de revisión humana; ninguno existe, y una puntuación "
        "automática de similitud no es una revisión por personas"
    ),
)

DERIVACION_A_SUPERVISION = DefinicionKPI(
    codigo="recuperacion.derivacion_a_supervision",
    nombre="Derivación a supervisión",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de turnos elegibles que el sistema derivó a la cola de "
        "revisión docente por degradación o por falta de fuente."
    ),
    unidad=Unidad.PROPORCION,
    numerador="elementos encolados en el periodo dentro del alcance",
    denominador=f"turnos elegibles. {TURNO_ELEGIBLE}",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("cola_revision", "historial_turno", "clase_matricula_historial"),
    limitaciones=(
        "Sólo se derivan las excepciones declaradas —degradado y sin-fuente—: "
        "no existe muestreo aleatorio de turnos correctos, así que la cifra no "
        "describe la cobertura de una supervisión por muestreo.",
        "Los elementos encolados antes de la migración 19 no llevan estudiante "
        "ni clase y no se pueden atribuir; el resultado los reporta como "
        "faltantes en vez de repartirlos.",
    ),
)

CATALOGO = (
    COBERTURA,
    TASA_SIN_FUENTE,
    DIVERSIDAD_DE_FUENTES,
    CONCENTRACION_DOCUMENTAL,
    APERTURA_DE_FUENTES,
    BLOQUES_VERIFICADOS,
    PRECISION_AUDITADA,
    DERIVACION_A_SUPERVISION,
)


REFERENCIAS_CONCEPTUALES = DefinicionKPI(
    codigo="recuperacion.referencias_conceptuales",
    nombre="Respuestas con referencia conceptual",
    dimension=Dimension.RECUPERACION,
    definicion_operacional=(
        "Proporción de turnos educativos completos cuya respuesta vinculó al "
        "menos una página de concepto del banco anclada en el material citado."
    ),
    unidad=Unidad.PROPORCION,
    numerador="turnos válidos con al menos un concepto enlazado desde el material citado",
    denominador="turnos educativos completos elegibles por matrícula histórica",
    poblacion_elegible=POBLACION_ELEGIBLE,
    fuentes=("historial_concepto", "historial_turno", "clase_matricula_historial"),
    depende_de_corpus=True,
    limitaciones=(
        "Mide referencias mostradas por el sistema; no mide conceptos intentados, comprendidos ni cubiertos del plan de clase.",
        "Un cero puede reflejar material sin páginas del banco vinculadas, aun cuando la respuesta trate el tema.",
    ),
)
CATALOGO = (*CATALOGO, REFERENCIAS_CONCEPTUALES)
