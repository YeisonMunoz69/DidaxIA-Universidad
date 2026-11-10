from dominio.kpi.contratos import DefinicionKPI, Dimension, Instrumento, MadurezMetodologica, Unidad
from dominio.modelo.factores_conductuales import NOMBRES, VERSION

CODIGOS = {
    "PS-Anx": "conductual.hibrido_ps_anx",
    "preconcepciones": "aprendizaje.preconcepciones_dialogo",
    "confirmacion": "conductual.hibrido_reiteracion",
}
DENOMINADORES = {
    "PS-Anx": "mensajes completos con lectura concluyente de tensión propia",
    "preconcepciones": "afirmaciones conceptuales propias con lectura concluyente",
    "confirmacion": "nuevos intentos verificables del mismo ejercicio tras corrección entregada, con lectura concluyente",
}
SUBTITULOS = {
    "PS-Anx": "lenguaje de tensión, análisis híbrido",
    "preconcepciones": "afirmaciones candidatas del diálogo",
    "confirmacion": "reiteración observada, análisis híbrido",
}


def _definir(factor):
    return DefinicionKPI(
        codigo=CODIGOS[factor],
        nombre=NOMBRES[factor] + " · " + SUBTITULOS[factor],
        dimension=Dimension.APRENDIZAJE if factor == "preconcepciones" else Dimension.CONDUCTUAL,
        definicion_operacional="Frecuencia de indicios corroborados por lectura semántica y controles deterministas entre "
        + DENOMINADORES[factor]
        + ".",
        unidad=Unidad.PROPORCION,
        numerador="oportunidades con detección corroborada",
        denominador=DENOMINADORES[factor],
        muestra_minima=5,
        poblacion_elegible="Estudiantes adultos con habilitación vigente, productor conductual histórico, matrícula histórica y turnos educativos completos no degradados.",
        fuentes=(
            "historial_turno",
            "analisis_conductual",
            "perfil_afectivo",
            "clase_matricula_historial",
        ),
        madurez_metodologica=MadurezMetodologica.EXPERIMENTAL,
        limitaciones=(
            "Frecuencia observable, no intensidad psicológica ni diagnóstico personal.",
            "Pendientes y coincidencias provisionales no entran en el porcentaje corroborado.",
            "No sustituye el sondeo de dos niveles ni demuestra un patrón en problemas análogos.",
            "El denominador cambia entre factores; sus porcentajes no se suman.",
        ),
        instrumento=Instrumento(
            nombre="Rúbrica de observables híbridos del diálogo",
            version=VERSION,
            constructo=NOMBRES[factor],
            escala="proporción de 0 a 1",
            regla_de_puntuacion="p = detecciones corroboradas / oportunidades concluyentes; pendientes separados",
            minimo_de_observaciones=5,
        ),
    )

CATALOGO = tuple(_definir(f) for f in NOMBRES)
