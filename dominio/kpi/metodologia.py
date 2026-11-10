"""Ficha pedagógica común a API, pantalla e informe; sin datos personales."""
from __future__ import annotations

from dominio.kpi.instrumentos import FUNDAMENTO, PROPUESTAS, VERSION

FUENTES = {
    "historial_turno": "Historial de turnos educativos registrados",
    "clase_matricula_historial": "Matrícula histórica y vigencia en la clase",
    "evento_telemetria": "Eventos explícitos de interacción",
    "historial_material": "Material recuperado para cada respuesta",
    "historial_bloque": "Bloques y verificación de las respuestas",
    "historial_concepto": "Conceptos del banco enlazados desde el material citado",
    "cola_revision": "Cola de revisión docente",
    "clase": "Clases registradas", "persona": "Perfiles autorizados",
}


def explicar(definicion) -> dict:
    from dominio.kpi.dimensiones.hibridos import CODIGOS  # noqa: PLC0415

    if definicion.codigo in CODIGOS.values():
        return {
            "version": definicion.instrumento.version, "pregunta": definicion.definicion_operacional,
            "formula": "p = x / n; porcentaje = 100 × p", "formula_latex": r"p=\frac{x}{n},\quad \%=100p",
            "simbolos": {"x": definicion.numerador, "n": definicion.denominador},
            "ejemplo": "2 detecciones de 10 oportunidades concluyentes: 20 %. Otras 5 pendientes quedan fuera y se informan aparte.",
            "alto": "Mayor frecuencia de los indicios definidos; no mayor intensidad psicológica.",
            "bajo": "Menor frecuencia registrada; cero no demuestra ausencia del factor.",
            "ausente": "Sin oportunidades concluyentes no se publica porcentaje; revisar cobertura y pendientes.",
            "incertidumbre": "La rúbrica es experimental. Las citas, negaciones, humor y referencias implícitas requieren contraste humano.",
            "fuentes": list(definicion.fuentes), "recoleccion": "Lecturas guardadas por turno y versión; consultar el informe no llama al modelo.",
            "regla_agregacion": "Se suman detecciones y oportunidades por hilo, no se promedian porcentajes individuales. Provisionales fuera del porcentaje.",
            "items": [], "escala_respuesta": "",
            "fundamento": "Adaptación operativa del anteproyecto y revisión PRISMA; no reproduce una escala ni el sondeo de dos niveles.",
            "prototipo": True,
        }
    if definicion.codigo.startswith("conductual.observable_"):
        return _explicar_dialogo(definicion)
    observables = {
        "conductual.ansiedad_matematica": (
            r"p_A=\frac{m_A}{m}",
            {"p_A": "frecuencia observada", "m_A": "mensajes con una o más coincidencias PS-Anx", "m": "mensajes educativos analizables"},
            "3 mensajes con coincidencia entre 12 analizables: 25 %.",
            "Más lenguaje reconocido; no mayor ansiedad psicológica.",
            "Menos coincidencias; cero no prueba ausencia de ansiedad.",
        ),
        "aprendizaje.concepciones_dos_niveles": (
            r"p_C=\frac{d_{16}+d_{21}+d_{22}+d_{23}}{s}",
            {"p_C": "fracción de sondeos tipificados", "d_i": "sondeos etiquetados con la concepción Mi", "s": "sondeos de dos niveles clasificados"},
            "2 sondeos etiquetados entre 8 clasificados: 25 %.",
            "Más respuestas tipificadas con una de las cuatro concepciones; no mide dominio total.",
            "Menos respuestas tipificadas; cero no descarta errores fuera de estos ítems.",
        ),
        "conductual.reiteracion_tras_correccion": (
            r"p_S=\frac{r}{o}",
            {"p_S": "fracción de oportunidades con repetición", "r": "propuestas incorrectas repetidas tras corrección", "o": "nuevos intentos verificables tras corrección en el mismo hilo y base"},
            "2 repeticiones en 5 oportunidades posteriores: 40 %.",
            "Más reiteración observable; dos episodios activan una hipótesis para revisión, no prueban sesgo cognitivo.",
            "Menos reiteración; cero no excluye sesgo fuera de las tareas verificables.",
        ),
    }
    if definicion.codigo in observables:
        latex, simbolos, ejemplo, alto, bajo = observables[definicion.codigo]
        incertidumbre = {
            "conductual.ansiedad_matematica": (
                "PS-Anx detecta sólo lenguaje explícito; negaciones, citas o ironía pueden "
                "alterar el recuento. Hace falta contraste con autoinforme y revisión humana."
            ),
            "aprendizaje.concepciones_dos_niveles": (
                "Sólo se clasifican sondeos de dos niveles. M16 aún necesita un ítem "
                "específico; hay que revisar la cobertura y el acuerdo de clasificación."
            ),
            "conductual.reiteracion_tras_correccion": (
                "Se compara texto normalizado en la misma tarea. La repetición no "
                "demuestra intención ni equivalencia matemática entre problemas."
            ),
        }[definicion.codigo]
        preguntas = {
            "conductual.ansiedad_matematica": "¿Qué proporción de mensajes analizables contiene lenguaje de tensión reconocido por PS-Anx?",
            "aprendizaje.concepciones_dos_niveles": "¿Qué proporción de sondeos clasificados presenta una de las concepciones instrumentadas?",
            "conductual.reiteracion_tras_correccion": "¿Con qué frecuencia se repite una propuesta incorrecta después de la corrección en la misma tarea?",
        }
        return {
            "version": VERSION, "pregunta": preguntas[definicion.codigo],
            "formula": definicion.formula, "formula_latex": latex,
            "simbolos": simbolos, "ejemplo": ejemplo, "alto": alto, "bajo": bajo,
            "ausente": "Sin oportunidades verificables no se calcula porcentaje; no se convierte en cero.",
            "incertidumbre": incertidumbre,
            "fuentes": [FUENTES.get(f, f.replace('_', ' ')) for f in definicion.fuentes],
            "recoleccion": "Turnos educativos completos del periodo y habilitación vigente; las oportunidades no observadas quedan fuera del cálculo.",
            "items": [], "escala_respuesta": "",
            "regla_agregacion": "Cada medida tiene su propio denominador; no se suman los tres fenómenos.",
            "fundamento": FUNDAMENTO, "prototipo": True,
        }
    propuesta = PROPUESTAS.get(definicion.codigo)
    formula = definicion.formula
    if propuesta:
        latex = propuesta["formula_latex"]
        simbolos = propuesta["simbolos"]
        ejemplo = propuesta["ejemplo"]
    elif "distribución" in definicion.denominador:
        latex = r"M=\operatorname{mediana}(x_1,\ldots,x_n)"
        simbolos = {"x_i": definicion.numerador, "n": "número de observaciones válidas", "M": "valor central; se acompaña de percentiles 25 y 75"}
        ejemplo = "Datos ilustrativos 1, 2, 3, 4 y 10: mediana 3; P25=2 y P75=4 por interpolación lineal. La publicación real exige el mínimo indicado."
    elif definicion.unidad.value == "conteo":
        latex = r"N=|\mathcal{E}|"
        simbolos = {"E": definicion.numerador, "N": "cantidad de elementos distintos que cumplen la definición"}
        ejemplo = "Si el conjunto elegible contiene 6 elementos que cumplen el criterio, N=6. Solo es cero cuando hubo población que observar."
    else:
        latex = r"p=\frac{x}{n},\qquad \%=100p"
        simbolos = {"x": definicion.numerador, "n": definicion.denominador, "p": "proporción entre 0 y 1; se presenta multiplicada por 100 como porcentaje"}
        ejemplo = "Con 6 casos que cumplen el criterio y 10 elegibles, p=6/10=0,60: se muestra 60%. Los números son ilustrativos."
    alto = "Un valor alto indica mayor cantidad o presencia de lo definido; no implica automáticamente un resultado mejor."
    bajo = "Un valor bajo indica menor cantidad o presencia de lo definido; no prueba falta de aprendizaje."
    if propuesta:
        alto = propuesta.get("alto", propuesta["criterio"])
        bajo = propuesta.get("bajo", "Un valor bajo se interpreta solo respecto al criterio de este instrumento; no describe a la persona fuera de la actividad observada.")
    return {
        "version": VERSION, "pregunta": propuesta["pregunta"] if propuesta else definicion.definicion_operacional,
        "formula": formula, "formula_latex": latex, "simbolos": simbolos,
        "ejemplo": ejemplo, "alto": alto, "bajo": bajo,
        "ausente": "Sin observaciones, sin fuente o sin muestra suficiente no hay puntuación. Un dato ausente nunca se sustituye por cero.",
        "incertidumbre": "Los datos describen el periodo y la población observada. La repetición de turnos de una misma persona no constituye una muestra independiente; no se ofrece confianza psicológica ni un intervalo causal.",
        "fuentes": [FUENTES.get(f, f.replace('_', ' ')) for f in definicion.fuentes],
        "recoleccion": propuesta["recoleccion"] if propuesta else "Se calcula con los registros existentes que satisfacen la definición y los filtros.",
        "items": propuesta["items"] if propuesta else [],
        "escala_respuesta": "1: nunca · 2: pocas veces · 3: algunas veces · 4: muchas veces · 5: siempre. Omitir o marcar N/A cuando no corresponda. Se requieren los tres ítems; no se imputan blancos." if propuesta and propuesta["items"] else "",
        "regla_agregacion": "Mediana de puntuaciones individuales completas, sin ponderar por frecuencia de uso." if propuesta and propuesta["familia"] in ("ordinal", "pareado") else "Aplicar la fórmula a las unidades elegibles definidas; no imputar respuestas ausentes.",
        "fundamento": FUNDAMENTO,
        "prototipo": bool(propuesta) or definicion.madurez.value == "experimental",
    }


def _explicar_dialogo(definicion):
    cambio = definicion.codigo.endswith("cambio_ayuda")
    return {
        "version": definicion.instrumento.version, "pregunta": definicion.definicion_operacional,
        "formula": definicion.formula,
        "formula_latex": r"\Delta=\operatorname{mediana}_i[100(p_{i,2}-p_{i,1})]" if cambio else r"p=\frac{x}{n}",
        "simbolos": {"p_1,p_2": "proporciones individuales en las dos mitades del periodo", "Delta": "mediana de cambios en puntos porcentuales"} if cambio else {"x": definicion.numerador, "n": definicion.denominador},
        "ejemplo": "Una persona pasa de 2/10 a 4/10 solicitudes: diferencia de +20 puntos porcentuales. Se agrega por persona, no por mensaje." if cambio else "Tres casos reconocidos en diez oportunidades: 3/10 = 30%. Los números son ilustrativos.",
        "alto": "Más presencia del comportamiento registrado; no indica automáticamente mejor aprendizaje.",
        "bajo": "Menos presencia reconocida; cero no demuestra ausencia fuera de las reglas o registros.",
        "ausente": "Sin oportunidades registradas no hay porcentaje. Los registros incompletos y ventanas truncadas se informan.",
        "incertidumbre": "Banco propio experimental. Candidatas conceptuales requieren contraste humano; resultados matemáticos incorrectos no demuestran una concepción estable. No estima confianza psicológica.",
        "fuentes": [FUENTES.get(f, f.replace('_', ' ')) for f in definicion.fuentes],
        "recoleccion": definicion.poblacion_elegible,
        "items": [], "escala_respuesta": "", "regla_agregacion": definicion.instrumento.regla_de_puntuacion,
        "fundamento": FUNDAMENTO, "prototipo": True,
    }
