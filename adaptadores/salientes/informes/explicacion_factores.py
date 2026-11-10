from xml.sax.saxutils import escape

from reportlab.platypus import PageBreak, Paragraph, Spacer

from dominio.kpi.dimensiones.hibridos import CODIGOS

ORIGINALES = {
    "conductual.ansiedad_matematica",
    "aprendizaje.concepciones_dos_niveles",
    "conductual.reiteracion_tras_correccion",
}


def contiene_factores(indicadores):
    return any(
        i.get("codigo") in ORIGINALES | set(CODIGOS.values())
        or str(i.get("codigo", "")).startswith("conductual.observable_")
        for i in indicadores
    )

def explicar_factores(indicadores, estilos):
    if not contiene_factores(indicadores):
        return []
    salida = [
        Paragraph("Cómo se mide cada factor actualmente en el laboratorio", estilos["Heading2"]),
        Paragraph("Fundamento e interpretación de los observables de DidaxIA", estilos["Heading3"]),
        Paragraph(
            "La revisión del proyecto distingue manifestaciones afectivas, explicaciones matemáticas y "
            "conductas observables durante la resolución. Estas dimensiones orientan el acompañamiento, "
            "pero los registros del chat no permiten observar directamente el estado interno de una persona. "
            "Por ello, las cifras de este informe describen frecuencias de evidencia registrada y se "
            "presentan como medidas experimentales, sin uso diagnóstico ni como calificación.",
            estilos["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("Ansiedad ante la resolución de problemas (PS-Anx)", estilos["Heading3"]),
        Paragraph(
            "Visscher y White distinguen la ansiedad asociada a resolver problemas no rutinarios de la "
            "ansiedad al explicar el razonamiento (A24). DidaxIA toma esa distinción como fundamento "
            "conceptual y registra lenguaje propio de tensión, miedo o preocupación durante el ejercicio. "
            "Expresiones como «me angustia equivocarme» pueden aportar evidencia; «no sé cómo empezar» "
            "expresa dificultad y, por sí sola, no acredita tensión. Esta lectura textual es una adaptación "
            "operativa del proyecto, no una aplicación ni una puntuación de la escala del estudio.",
            estilos["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("Preconcepciones erróneas", estilos["Heading3"]),
        Paragraph(
            "Una respuesta incorrecta puede proceder de una regla mal comprendida, un cálculo puntual o "
            "una escritura ambigua. El diagnóstico de dos niveles vincula respuesta y razón para "
            "distinguir estas posibilidades, como en el sistema de Yang y colaboradores (C27). En el "
            "diálogo libre, DidaxIA registra como candidata una relación errónea sostenida por el "
            "estudiante, por ejemplo «dividir por cero da cero». Una respuesta numérica aislada no basta "
            "para atribuir una concepción estable. Las candidatas del chat y los sondeos formales se "
            "calculan por separado y conservan sus códigos e instrumentos.",
            estilos["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("Sesgo de confirmación", estilos["Heading3"]),
        Paragraph(
            "El anteproyecto adopta una aproximación observable a este factor mediante la reiteración "
            "de una estrategia incorrecta después de recibir retroalimentación correctiva. El análisis "
            "del chat exige constancia del problema, de la corrección entregada y de un nuevo intento "
            "matemático verificable; si el nuevo resultado es correcto, no se cuenta como reiteración. "
            "Pedir «explícame de nuevo» no demuestra insistencia en un error. Un episodio describe "
            "reincidencia; el patrón longitudinal del instrumento original requiere dos episodios y "
            "no queda demostrado por una frase ni por el porcentaje híbrido del mismo ejercicio.",
            estilos["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("Cómo interpretar las cifras", estilos["Heading3"]),
        Paragraph(
            "Cada proporción divide las detecciones por las oportunidades que declara su ficha y se "
            "presenta de 0 a 100 %. En el análisis híbrido sólo entran oportunidades concluyentes; las "
            "coincidencias provisionales, lecturas fallidas y decisiones dudosas se informan aparte. "
            "Por ejemplo, 2 detecciones en 10 oportunidades concluyentes equivalen a 20 %; si existen "
            "otras 5 oportunidades pendientes, esa cifra describe las 10 evaluadas, no las 15. Los "
            "factores tienen denominadores distintos y pueden coincidir en un mismo turno, por lo que "
            "sus porcentajes no se suman ni representan una probabilidad psicológica.",
            estilos["Normal"],
        ),
        Paragraph(
            "«Sin datos» indica falta de oportunidades concluyentes, mientras que 0 % indica que hubo "
            "oportunidades evaluadas sin detecciones bajo ese método. «Muestra insuficiente» conserva "
            "los conteos sin publicar una proporción por debajo del mínimo del instrumento. Una cifra "
            "elevada con pocas observaciones requiere examinar numerador, denominador, cobertura y "
            "versiones antes de comparar estudiantes o periodos. Los análisis retrospectivos conservan "
            "la fecha del mensaje y una fecha de relectura; no sustituyen los cortes originales del piloto.",
            estilos["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("Métodos incluidos en este informe", estilos["Heading3"]),
    ]
    for item in indicadores:
        codigo = item.get("codigo", "")
        if codigo not in ORIGINALES | set(CODIGOS.values()):
            continue
        instrumento = item.get("instrumento") or {}
        salida.append(
            Paragraph(
                "<b>"
                + escape(item.get("nombre", codigo))
                + ".</b> "
                + escape(item.get("definicion_operacional", "Consultar la ficha del indicador."))
                + " Instrumento: "
                + escape(instrumento.get("version", "versión declarada en la ficha"))
                + ".",
                estilos["Normal"],
            )
        )
        detalle = item.get("detalle") or {}
        if detalle.get("ultima_lectura"):
            salida.append(
                Paragraph(
                    "Última lectura registrada: "
                    + escape(detalle["ultima_lectura"])
                    + ". Mensajes con lectura histórica: "
                    + str(detalle.get("origenes_lecturas", {}).get("relectura", 0))
                    + ". Modelos observados: "
                    + escape(", ".join(detalle.get("modelos_analisis", [])))
                    + ".",
                    estilos["Normal"],
                )
            )
    salida.extend(
        [
            Spacer(1, 8),
            Paragraph("Fuentes y alcance de la adaptación", estilos["Heading3"]),
            Paragraph(
                "A24. Visscher, D. y White, N. (2020). <i>Measuring Mathematics Engagement Anxiety: "
                "New Dimensions of Math Anxiety in an RMARS-Addendum</i>. "
                '<link href="https://doi.org/10.1007/s40753-019-00104-6">doi:10.1007/s40753-019-00104-6</link>.',
                estilos["Normal"],
            ),
            Paragraph(
                "C27. Yang, T.-C., Fu, H.-T., Hwang, G.-J. y Yang, S. J. H. (2017). "
                "<i>Development of an interactive mathematics learning system based on a two-tier "
                "test diagnostic and guiding strategy</i>. "
                '<link href="https://doi.org/10.14742/ajet.2154">doi:10.14742/ajet.2154</link>.',
                estilos["Normal"],
            ),
            Paragraph(
                "Los identificadores A24 y C27 corresponden a la revisión PRISMA del proyecto. "
                "La rúbrica de conversación y sus fórmulas son decisiones del prototipo DidaxIA; "
                "estos antecedentes no validan automáticamente su detección en español colombiano "
                "ni una medición psicológica del sesgo de confirmación.",
                estilos["Normal"],
            ),
            PageBreak(),
        ]
    )
    return salida
