from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _participacion(curso, presentacion, parrafo):
    historia = [parrafo(curso['nombre'], 'Heading2')]
    titular = 'Docente' if curso.get('audiencia') == 'docentes' else 'Estudiante'
    poblacion = 'Docentes destinatarios' if curso.get('audiencia') == 'docentes' else 'Matrícula actual'
    if presentacion:
        historia.extend([parrafo(f"Publicado: {curso['publicada_en']}"), parrafo(
            f"{poblacion}: {curso['matriculados']} · Abrieron: {curso['vieron']} · "
            f"Pendientes de abrir: {curso['matriculados'] - curso['vieron']} · "
            f"Aperturas de destinatarios actuales: {curso['aperturas']} · "
            f"Aperturas históricas del envío: {curso['aperturas_historicas']}"
        )])
        if not curso['conteo_completo']:
            historia.append(parrafo('Los registros anteriores al contador detallado conservan al menos una apertura por estudiante.'))
        filas = [[parrafo(titular), parrafo('Estado'), parrafo('Aperturas'), parrafo('Última apertura')]]
        filas.extend([[parrafo(i['nombre']), parrafo('Abiertas' if i['vista'] else 'Pendiente'),
                       parrafo(i['aperturas']), parrafo(i['ultima_en'] or '—')] for i in curso['integrantes']])
        anchos = [6 * cm, 3 * cm, 2 * cm, 5 * cm]
    else:
        historia.append(parrafo(
            f"{poblacion}: {curso['matriculados']} · Respondieron: {curso['respondieron']} · "
            f"Pendientes: {curso['matriculados'] - curso['respondieron']} · Vieron: {curso['vieron']} · "
            f"Respuestas históricas: {curso['respuestas_totales']}"
        ))
        filas = [[parrafo(titular), parrafo('Respuesta'), parrafo('Recurso abierto')]]
        filas.extend([[parrafo(i['nombre']), parrafo('Enviada' if i['respondida'] else 'Pendiente'),
                       parrafo('Sí' if i['vista'] else 'No')] for i in curso['integrantes']])
        anchos = [9 * cm, 3 * cm, 4 * cm]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf0f5')),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                              ('LINEBELOW', (0, 0), (-1, -1), .3, colors.lightgrey)]))
    historia.extend([tabla, Spacer(1, .5 * cm)])
    return historia

def generar_pdf(metricas):
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    historia = []

    def parrafo(texto, estilo='BodyText'):
        return Paragraph(escape(str(texto)), estilos[estilo])

    historia.extend([parrafo('DidaxIa · Informe de recursos', 'Title'), parrafo(metricas['titulo'], 'Heading1'),
                     parrafo('Generado: ' + datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')),
                     parrafo('Estado: ' + metricas['estado']), Spacer(1, .5 * cm)])
    cursos = [c for c in metricas['cursos'] if not metricas['clase_filtro'] or c['id'] == metricas['clase_filtro']]
    if metricas.get('envio_actual'):
        historia.append(parrafo(f"Envío {metricas['envio_actual']} · métricas independientes de los demás envíos", 'Heading2'))
    for curso in cursos:
        historia.extend(_participacion(curso, metricas['tipo'] == 'diapositivas', parrafo))
    historia.append(parrafo('Las listas de participación usan la matrícula actual; los resultados incluyen todas las respuestas enviadas antes de un retiro. Las visitas acreditan apertura, no lectura completa. En selección múltiple los porcentajes pueden sumar más de 100 %.'))
    for pregunta in metricas['preguntas']:
        historia.extend([parrafo(pregunta['titulo'], 'Heading2'), parrafo(f"Respuestas a esta pregunta: {pregunta['respondidas']}")])
        if pregunta['promedio'] is not None:
            historia.append(parrafo(f"Promedio: {pregunta['promedio']:.2f}"))
        frecuencias = pregunta['frecuencias']
        if frecuencias:

            for offset in range(0, len(frecuencias), 12):
                grupo = frecuencias[offset:offset + 12]
                d = Drawing(440, max(120, len(grupo) * 20 + 50))
                barras = HorizontalBarChart()
                barras.x, barras.y, barras.width, barras.height = 35, 25, 350, d.height - 50
                barras.data = [[f['cantidad'] for f in grupo]]
                barras.categoryAxis.categoryNames = [str(offset + i + 1) for i in range(len(grupo))]
                barras.valueAxis.valueMin = 0
                barras.valueAxis.valueMax = max(1, max(f['cantidad'] for f in grupo))
                barras.bars[0].fillColor = colors.HexColor('#863454')
                d.add(barras)
                historia.append(d)
            filas = [[parrafo('Opción'), parrafo('Cantidad'), parrafo('% de quienes respondieron')]]
            filas.extend([[parrafo(f"{i+1}. {f['etiqueta']}"), parrafo(f['cantidad']),
                           parrafo(f"{f['cantidad']/pregunta['respondidas']*100:.1f} %" if pregunta['respondidas'] else '0 %')]
                          for i, f in enumerate(frecuencias)])
            historia.append(Table(filas, colWidths=[9 * cm, 2 * cm, 5 * cm], repeatRows=1))
            if pregunta['tipo'] != 'multiple' and sum(f['cantidad'] for f in frecuencias) and len(frecuencias) <= 12:
                d = Drawing(440, 175)
                pie = Pie()
                pie.x, pie.y, pie.width, pie.height = 130, 20, 130, 130
                pie.data = [f['cantidad'] for f in frecuencias]
                pie.labels = [str(i + 1) for i in range(len(frecuencias))]
                d.add(pie)
                historia.append(d)
        for respuesta in pregunta['textos']:
            historia.append(parrafo(respuesta))
    SimpleDocTemplate(salida, pagesize=(21 * cm, 29.7 * cm), rightMargin=2 * cm,
                      leftMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm).build(historia)
    return salida.getvalue()
