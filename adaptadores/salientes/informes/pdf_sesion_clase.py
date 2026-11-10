from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from statistics import median
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from adaptadores.salientes.informes.graficas_pdf import (
    barras_horizontales,
    perfil_proporciones,
    serie_temporal,
)

ZONA = ZoneInfo("America/Bogota")
METRICAS = {
    "matriculados": "Estudiantes matriculados en la cohorte actual",
    "activos": "Estudiantes con al menos un turno elegible",
    "adopcion": "Porcentaje de estudiantes con actividad",
    "turnos": "Turnos elegibles",
    "conversaciones": "Conversaciones con turnos elegibles",
    "mediana_turnos": "Mediana de turnos por estudiante",
    "turnos_por_activo": "Turnos por estudiante con actividad",
    "respuestas_con_fuente": "Respuestas no degradadas con fuente",
    "proporcion_con_fuente": "Porcentaje de respuestas no degradadas con fuente",
}
PREDETERMINADAS = ("matriculados", "activos", "adopcion", "turnos", "conversaciones", "respuestas_con_fuente")
INTERPRETACION = {
    "matriculados": "Tamaño de la cohorte matriculada usada como referencia; no indica participación.",
    "activos": "Personas con al menos un turno elegible; no mide aprendizaje ni calidad.",
    "adopcion": "Activos divididos por matriculados. Con pocos estudiantes, una persona cambia mucho el porcentaje.",
    "turnos": "Interacciones educativas completadas en el intervalo; no equivalen a ejercicios resueltos.",
    "conversaciones": "Hilos con actividad elegible; un mismo estudiante puede abrir varios.",
    "mediana_turnos": "Valor central de turnos por estudiante, incluidos quienes no tuvieron actividad.",
    "turnos_por_activo": "Promedio de turnos entre estudiantes activos; no describe a quienes no ingresaron.",
    "respuestas_con_fuente": "Respuestas no degradadas con fuente; la presencia de fuente no garantiza exactitud.",
    "proporcion_con_fuente": "Respuestas con fuente divididas por turnos elegibles; no es una nota de calidad.",
}


def _fuentes() -> tuple[str, str]:
    import reportlab

    raiz = Path(reportlab.__file__).resolve().parent / "fonts"
    normal, negrita = raiz / "Vera.ttf", raiz / "VeraBd.ttf"
    if normal.is_file() and negrita.is_file():
        if "DidaxIASesion" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DidaxIASesion", normal))
            pdfmetrics.registerFont(TTFont("DidaxIASesion-Bold", negrita))
        return "DidaxIASesion", "DidaxIASesion-Bold"
    return "Helvetica", "Helvetica-Bold"

def parametros_reporte(
    desde_crudo: str | None, hasta_crudo: str | None,
    metricas_crudas: str | None, kpis_crudos: str | None = None,
):

    if not desde_crudo or not hasta_crudo:
        raise ValueError("desde y hasta deben incluir fecha, hora y zona horaria")
    try:
        desde = datetime.fromisoformat(desde_crudo.replace("Z", "+00:00"))
        hasta = datetime.fromisoformat(hasta_crudo.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("fecha u hora no válida") from exc
    if desde.tzinfo is None or hasta.tzinfo is None:
        raise ValueError("desde y hasta deben indicar la zona horaria")
    if hasta <= desde or hasta - desde > timedelta(days=31):
        raise ValueError("el intervalo debe ser positivo y no superar 31 días")
    metricas = tuple(dict.fromkeys((metricas_crudas or ",".join(PREDETERMINADAS)).split(",")))
    if not metricas or any(m not in METRICAS for m in metricas):
        raise ValueError("selección de métricas no válida")
    kpis = tuple(dict.fromkeys(kpis_crudos.split(","))) if kpis_crudos else ()
    if len(kpis) > 10 or any(not codigo or len(codigo) > 100 for codigo in kpis):
        raise ValueError("selección de KPI no válida")
    return desde.astimezone(ZONA), hasta.astimezone(ZONA), metricas, kpis

def armar_reporte(
    actividad: dict, metricas: tuple[str, ...], desde: datetime, hasta: datetime,
    kpi: dict | None = None, consumo_ia: dict | None = None,
) -> dict:
    if actividad.get("truncado"):
        raise ValueError("la clase supera el máximo de filas del reporte; no se publicarán totales parciales")
    filas = actividad.get("estudiantes", [])
    turnos = sum(int(f.get("turnos_elegibles") or 0) for f in filas)
    activos = sum(int(f.get("turnos_elegibles") or 0) > 0 for f in filas)
    total = len(filas)
    con_fuente = sum(int(f.get("respuestas_con_fuente") or 0) for f in filas)
    valores = {
        "matriculados": total,
        "activos": activos,
        "adopcion": round(100 * activos / total, 1) if total else None,
        "turnos": turnos,
        "conversaciones": sum(int(f.get("conversaciones") or 0) for f in filas),
        "mediana_turnos": median(int(f.get("turnos_elegibles") or 0) for f in filas) if filas else None,
        "turnos_por_activo": round(turnos / activos, 2) if activos else None,
        "respuestas_con_fuente": con_fuente,
        "proporcion_con_fuente": round(100 * con_fuente / turnos, 1) if turnos else None,
    }
    return {
        "version": "reporte-sesion-clase.v1",
        "clase": actividad["clase"],
        "periodo": {"desde": desde.isoformat(), "hasta_exclusivo": hasta.isoformat(), "zona": "America/Bogota"},
        "generado_en": datetime.now(ZONA).replace(microsecond=0).isoformat(),
        "metricas": [{"codigo": m, "nombre": METRICAS[m], "valor": valores[m],
                       "interpretacion": INTERPRETACION[m]} for m in metricas],
        "kpi_oficiales": kpi["indicadores"] if kpi else [],
        "version_catalogo_kpi": kpi.get("version_catalogo") if kpi else None,
        "referencia_ia": ({
            "alcance": "institucional; no atribuible a esta clase ni a sus estudiantes",
            "proveedor": "DeepSeek",
            "totales": consumo_ia["totales"],
            "costos": consumo_ia["costos"],
            "por_modelo": consumo_ia.get("por_modelo", []),
            "serie_diaria": consumo_ia.get("serie_diaria", []),
            "regla_supresion": consumo_ia.get("regla_supresion"),
        } if consumo_ia is not None else None),
        "estudiantes": [
            {
                "alias": f["alias_proyeccion"],
                "turnos": f.get("turnos_elegibles", 0),
                "conversaciones": f.get("conversaciones", 0),
                "ultima_actividad": (
                    datetime.fromisoformat(f["ultima_actividad"]).astimezone(ZONA).isoformat()
                    if f.get("ultima_actividad") else None
                ),
            }
            for f in filas
        ],
        "metodo": "Las métricas descriptivas cuentan turnos educativos completos de la cohorte actualmente matriculada, desde su matrícula, en [desde, hasta). Los KPI oficiales mantienen sus propias definiciones, población y estados de calidad.",
        "limitaciones": [
            "La actividad observada no mide aprendizaje, calificación ni causalidad.",
            "La clase histórica del turno no se registra; la atribución usa la cohorte actual desde la matrícula.",
            "Antes de usar las cifras en investigación, verificar por separado la elegibilidad y autorización vigente de cada participante.",
            "Las llamadas de IA no registran una relación verificable con la clase; "
            + ("la referencia DeepSeek es institucional y no debe dividirse entre estos estudiantes."
               if consumo_ia is not None else "por defecto se excluyen de este reporte."),
        ],
    }

def _seccion_ia(referencia: dict | None, estilos, normal: str, negrita: str) -> list:
    if referencia is None:
        return []
    totales = referencia["totales"]
    costos = referencia["costos"]

    def legible(valor: object) -> str:
        return "Sin dato" if valor is None else escape(str(valor))

    filas = [
        ["Llamadas", "Medidas", "Sin medición", "Entrada", "Salida"],
        [legible(totales.get(clave)) for clave in
         ("llamadas", "medidas", "sin_medicion", "entrada_total", "salida")],
    ]
    tabla = Table(filas, colWidths=[3.2 * cm] * 5, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), negrita),
        ("FONTNAME", (0, 1), (-1, -1), normal),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C8D4DF")),
    ]))
    completo = costos.get("estimado_usd")
    elementos = [
        Spacer(1, .35 * cm),
        Paragraph("Referencia de consumo DeepSeek del mismo intervalo", estilos["Heading2"]),
        Paragraph(
            "Total de toda DidaxIA durante [desde, hasta), no consumo de esta clase. "
            "No se vinculan llamadas con estudiantes ni se infiere gasto por turno.",
            estilos["Normal"],
        ),
        Spacer(1, .15 * cm), tabla, Spacer(1, .2 * cm),
        KeepTogether([
            barras_horizontales("Tokens DeepSeek medidos", [
                ("Entrada", totales.get("entrada_total")),
                ("Salida", totales.get("salida")),
            ]),
            Paragraph("Comparación de cantidades de tokens registrados; las llamadas sin "
                      "medición no se representan como cero.", estilos["Normal"]),
        ]),
        Paragraph(
            "Costo API estimado USD del intervalo: "
            + (legible(completo) if completo is not None else "no calculable íntegramente")
            + ". Subtotal de llamadas calculables: "
            + legible(costos.get("subtotal_calculable_usd"))
            + ". Faltan medición o tarifa en "
            + legible(costos.get("llamadas_sin_tarifa_o_medicion"))
            + " llamada(s). Es una estimación, no una factura ni un costo de la clase.",
            estilos["Normal"],
        ),
    ]
    dias = referencia.get("serie_diaria", [])
    if any(fila.get("costo_usd") is not None for fila in dias):
        elementos += [
            Spacer(1, .2 * cm),
            KeepTogether([
                serie_temporal("Costo API estimado por día [USD]", [
                    (str(fila.get("fecha", "")), fila.get("costo_usd")) for fila in dias
                ]),
                Paragraph(
                    "Sólo se unen días consecutivos con costo completo y conteo publicable. "
                    "Un hueco representa supresión o falta de tarifa/medición, no gasto cero.",
                    estilos["Normal"],
                ),
            ]),
        ]
    else:
        elementos.append(Paragraph(
            "No se publica serie de costo diario: el desglose está suprimido o no tiene "
            "medición y tarifa suficientes. El total del intervalo permanece visible arriba.",
            estilos["Normal"],
        ))
    return elementos

def _grafica_kpi_seleccionados(indicadores: list[dict], estilos) -> list:
    figura = perfil_proporciones("KPI seleccionados · escala 0–100 %", indicadores)
    if figura is None:
        return []
    return [
        figura,
        Paragraph(
            "Cada barra muestra un valor publicado y su muestra; los KPI tienen "
            "definiciones distintas y no se ordenan como niveles de logro.",
            estilos["Normal"],
        ),
        Spacer(1, .15 * cm),
    ]

def generar_pdf(reporte: dict) -> bytes:
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
                                  topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    normal, negrita = _fuentes()
    estilos["Normal"].fontName = normal
    estilos["Title"].fontName = negrita
    estilos["Heading2"].fontName = negrita
    for nombre in ("Title", "Heading2"):
        estilos[nombre].textColor = colors.black
    cuerpo = [
        Paragraph("DidaxIA · reporte de uso de clase", estilos["Title"]),
        Paragraph(escape(reporte["clase"]["nombre"]), estilos["Heading2"]),
        Paragraph(f"Desde: {escape(reporte['periodo']['desde'])}<br/>Hasta exclusivo: {escape(reporte['periodo']['hasta_exclusivo'])}<br/>Zona: America/Bogota<br/>Generado: {escape(reporte['generado_en'])}", estilos["Normal"]),
        Spacer(1, .35 * cm),
    ]
    from adaptadores.salientes.informes.explicacion_factores import (
        explicar_factores,
    )

    cuerpo.extend(explicar_factores(reporte["kpi_oficiales"], estilos))
    cuerpo.append(Paragraph("Métricas seleccionadas", estilos["Heading2"]))
    filas = [["Métrica", "Valor"]] + [
        [m["nombre"], "Sin dato" if m["valor"] is None else
         f"{m['valor']}%" if m["codigo"] in ("adopcion", "proporcion_con_fuente") else str(m["valor"])]
        for m in reporte["metricas"]
    ]
    tabla = Table(filas, colWidths=[13 * cm, 3 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), negrita),
        ("FONTNAME", (0, 1), (-1, -1), normal),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C8D4DF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    cuerpo += [tabla, Spacer(1, .25 * cm)]
    for metrica in reporte["metricas"]:
        cuerpo.append(Paragraph(
            f"<b>{escape(metrica['nombre'])}:</b> {escape(metrica['interpretacion'])}",
            estilos["Normal"],
        ))
        cuerpo.append(Spacer(1, .12 * cm))
    def tramos(campo: str, singular: str, plural: str) -> list[tuple[str, int]]:
        conteos = {f"0 {plural}": 0, f"1 {singular}": 0,
                   f"2 a 4 {plural}": 0, f"5 o más {plural}": 0}
        for fila in reporte["estudiantes"]:
            cantidad = int(fila.get(campo) or 0)
            indice = 0 if cantidad == 0 else 1 if cantidad == 1 else 2 if cantidad < 5 else 3
            tramo = list(conteos)[indice]
            conteos[tramo] += 1
        return list(conteos.items())

    cuerpo += [Spacer(1, .25 * cm), KeepTogether([
                   barras_horizontales("Estudiantes por tramo de turnos", tramos("turnos", "turno", "turnos")),
                   Paragraph("La figura distribuye a la cohorte actual por turnos elegibles del corte; "
                             "no clasifica desempeño ni compara aprendizaje.", estilos["Normal"]),
               ]),
               Spacer(1, .2 * cm),
               KeepTogether([
                   barras_horizontales("Estudiantes por tramo de conversaciones", tramos("conversaciones", "conversación", "conversaciones")),
                   Paragraph("Una conversación puede contener varios turnos. Los dos gráficos tienen "
                             "unidades distintas y no deben sumarse.", estilos["Normal"]),
               ]),
               Spacer(1, .35 * cm), Paragraph("Detalle seudonimizado", estilos["Heading2"])]
    detalle = [["Alias", "Turnos", "Conversaciones", "Última actividad"]]
    detalle += [[f["alias"], str(f["turnos"]), str(f["conversaciones"]),
                 (f["ultima_actividad"] or "Sin actividad").replace("T", " ")] for f in reporte["estudiantes"]]
    if len(detalle) == 1:
        detalle.append(["Sin estudiantes", "", "", ""])
    tabla_detalle = Table(detalle, colWidths=[3 * cm, 2 * cm, 3 * cm, 8 * cm], repeatRows=1)
    tabla_detalle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), negrita),
        ("FONTNAME", (0, 1), (-1, -1), normal),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C8D4DF")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
    ]))
    cuerpo += [tabla_detalle]
    if reporte["kpi_oficiales"]:
        cuerpo += [Spacer(1, .35 * cm), Paragraph("KPI oficiales seleccionados", estilos["Heading2"])]
        cuerpo.extend(_grafica_kpi_seleccionados(reporte["kpi_oficiales"], estilos))
        filas_kpi = [["KPI", "Estado", "Valor"]]
        for indicador in reporte["kpi_oficiales"]:
            valor = indicador.get("valor")
            if valor is not None and indicador.get("unidad") == "proporcion":
                valor = f"{valor * 100:.1f}%"
            filas_kpi.append([
                Paragraph(escape(indicador["nombre"]), estilos["Normal"]),
                Paragraph(escape(indicador["estado"]), estilos["Normal"]),
                Paragraph(escape("—" if valor is None else str(valor)), estilos["Normal"]),
            ])
        tabla_kpi = Table(filas_kpi, colWidths=[9 * cm, 4 * cm, 3 * cm], repeatRows=1)
        tabla_kpi.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), negrita),
            ("FONTNAME", (0, 1), (-1, -1), normal),
            ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C8D4DF")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]))
        cuerpo.append(tabla_kpi)
        for indicador in reporte["kpi_oficiales"]:
            cuerpo.append(Paragraph(
                f"<b>{escape(str(indicador.get('nombre') or indicador.get('codigo') or 'KPI'))}:</b> "
                f"{escape(str(indicador.get('interpretacion') or indicador.get('motivo_no_calculo') or 'No hay interpretación publicada para este corte.'))} "
                f"Estado: {escape(str(indicador.get('estado') or 'sin dato'))}. "
                f"Muestra: {escape(str(indicador.get('muestra') if indicador.get('muestra') is not None else 'sin dato'))}.",
                estilos["Normal"],
            ))
        cuerpo.append(Paragraph(f"Catálogo KPI: {escape(str(reporte['version_catalogo_kpi']))}", estilos["Normal"]))
    cuerpo += _seccion_ia(reporte.get("referencia_ia"), estilos, normal, negrita)
    cuerpo += [Spacer(1, .35 * cm), Paragraph("Método y límites", estilos["Heading2"]),
               Paragraph(escape(reporte["metodo"]), estilos["Normal"])]
    cuerpo += [Paragraph("• " + escape(aviso), estilos["Normal"]) for aviso in reporte["limitaciones"]]
    documento.build(cuerpo)
    return salida.getvalue()
