"""PDF determinista del módulo financiero-operativo de consumo de IA."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from adaptadores.salientes.informes.graficas_pdf import (
    barras_horizontales,
    lollipop_horizontal,
    serie_temporal,
)

VERSION_PLANTILLA = "consumo-ia-institucional-1.2"


def _fuentes() -> tuple[str, str]:
    import reportlab  # noqa: PLC0415

    raiz = Path(reportlab.__file__).resolve().parent / "fonts"
    normal, negrita = raiz / "Vera.ttf", raiz / "VeraBd.ttf"
    if normal.is_file() and negrita.is_file():
        if "DidaxIAConsumo" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DidaxIAConsumo", normal))
            pdfmetrics.registerFont(TTFont("DidaxIAConsumo-Bold", negrita))
        return "DidaxIAConsumo", "DidaxIAConsumo-Bold"
    return "Helvetica", "Helvetica-Bold"


def _texto(valor: object) -> str:
    return "—" if valor is None or valor == "" else escape(str(valor))


def _tabla(filas, anchos) -> Table:
    normal, negrita = _fuentes()
    celda = ParagraphStyle("ConsumoCelda", fontName=normal, fontSize=7.2, leading=9)
    cabecera = ParagraphStyle(
        "ConsumoCabecera", parent=celda, fontName=negrita, textColor=colors.black
    )
    contenido = [
        [Paragraph(_texto(valor), cabecera if indice == 0 else celda) for valor in fila]
        for indice, fila in enumerate(filas)
    ]
    tabla = Table(contenido, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D4DF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _pie(canvas, documento) -> None:
    canvas.saveState()
    canvas.setFont(_fuentes()[0], 7)
    canvas.setFillColor(colors.black)
    canvas.drawString(1.7 * cm, 1.0 * cm, f"DidaxIA · {VERSION_PLANTILLA}")
    canvas.drawRightString(A4[0] - 1.7 * cm, 1.0 * cm, f"Página {documento.page}")
    canvas.restoreState()


def generar_informe_consumo_ia(datos: dict, *, secciones: frozenset[str] | None = None) -> bytes:
    normal, negrita = _fuentes()
    estilos = getSampleStyleSheet()
    estilos["Normal"].fontName = normal
    estilos["Normal"].fontSize = 8.5
    estilos["Normal"].leading = 12
    for nombre in ("Title", "Heading1", "Heading2"):
        estilos[nombre].fontName = negrita
        estilos[nombre].textColor = colors.black
    estilos.add(
        ParagraphStyle(
            "ConsumoAviso",
            parent=estilos["Normal"],
            borderColor=colors.black,
            borderWidth=0.7,
            borderPadding=7,
            backColor=colors.white,
        )
    )
    estilos.add(
        ParagraphStyle(
            "ConsumoPortada", parent=estilos["Normal"], alignment=TA_CENTER, fontSize=11
        )
    )
    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Consumo institucional de IA - DidaxIA",
        author="DidaxIA",
        invariant=1,
    )
    periodo = datos.get("periodo", {})
    totales = datos.get("totales", {})
    costos = datos.get("costos", {})
    trm = datos.get("trm_actual", {})
    historia = [
        Spacer(1, 1.2 * cm),
        Paragraph("DidaxIA", estilos["ConsumoPortada"]),
        Paragraph("Consumo institucional de inteligencia artificial", estilos["Title"]),
        Paragraph(
            f"Periodo semiabierto [{_texto(periodo.get('desde'))}, {_texto(periodo.get('hasta'))}) · America/Bogota",
            estilos["ConsumoPortada"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Módulo financiero-operativo separado del catálogo de KPI educativos. Los importes "
            "son estimaciones reproducibles; no son cargos reales de facturación. Los "
            "proveedores locales tienen costo API cero y costo de infraestructura no calculado.",
            estilos["ConsumoAviso"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph("Cobertura y totales", estilos["Heading1"]),
        _tabla(
            [
                ["Llamadas", "Medidas", "Sin medición", "Fallidas", "Tokens entrada", "Tokens salida"],
                [totales.get("llamadas"), totales.get("medidas"), totales.get("sin_medicion"),
                 totales.get("fallidas"), totales.get("entrada_total"), totales.get("salida")],
            ],
            [2.5 * cm, 2.5 * cm, 2.8 * cm, 2.5 * cm, 3 * cm, 3 * cm],
        ),
        Spacer(1, 0.25 * cm),
        barras_horizontales(
            "Estado de medición de llamadas",
            [("Con medición", totales.get("medidas")),
             ("Sin medición", totales.get("sin_medicion")),
             ("Fallidas", totales.get("fallidas"))],
        ),
        Paragraph(
            "Son conteos operativos del periodo. Una llamada fallida puede coincidir con "
            "otra categoría; no sume estas barras como si fueran partes excluyentes.",
            estilos["Normal"],
        ),
        Spacer(1, .2 * cm),
        barras_horizontales(
            "Tokens medidos por dirección",
            [("Entrada", totales.get("entrada_total")),
             ("Salida", totales.get("salida"))],
        ),
        Paragraph(
            "Se comparan cantidades de tokens, no precios. La ausencia de medición no se "
            "representa como cero.", estilos["Normal"],
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("Costo estimado y conversión", estilos["Heading1"]),
        _tabla(
            [
                ["Estimación completa USD", "Subtotal calculable USD", "Estimación completa COP", "TRM oficial"],
                [costos.get("estimado_usd"), costos.get("subtotal_calculable_usd"),
                 costos.get("estimado_cop"),
                 f"{_texto(trm.get('pesos_por_usd'))} · {_texto(trm.get('fecha'))}"],
            ],
            [4.1 * cm, 4.1 * cm, 4.1 * cm, 4.1 * cm],
        ),
        Paragraph(
            "Una estimación completa aparece sólo cuando cada llamada externa tiene medición, "
            "tarifa vigente y TRM histórica. Una ausencia se muestra como raya, nunca como cero.",
            estilos["Normal"],
        ),
        Spacer(1, 0.35 * cm),
        Paragraph("Desglose por proveedor y modelo", estilos["Heading1"]),
        _tabla(
            [["Proveedor", "Modelo", "Llamadas", "Medidas", "Cache hit", "Cache miss", "Entrada", "Salida"]]
            + [
                [fila.get("proveedor"), fila.get("modelo"), fila.get("llamadas"),
                 fila.get("medidas"), fila.get("entrada_cache_hit"),
                 fila.get("entrada_cache_miss"), fila.get("entrada_total"), fila.get("salida")]
                for fila in datos.get("por_modelo", [])
            ],
            [2 * cm, 4.6 * cm, 1.7 * cm, 1.7 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm],
        ),
        Spacer(1, .25 * cm),
        KeepTogether([
            lollipop_horizontal(
                "Llamadas por proveedor y modelo (máximo diez)",
                [(f"{fila.get('proveedor', '')} / {fila.get('modelo', '')}", fila.get("llamadas"))
                 for fila in sorted(datos.get("por_modelo", []),
                                    key=lambda item: (-int(item.get("llamadas") or 0),
                                                      str(item.get("modelo", ""))))[:10]],
            ),
            Paragraph(
                "La frecuencia de llamadas no equivale a costo ni a calidad de respuesta. "
                "El desglose tabular conserva los modelos incluidos en el corte.", estilos["Normal"],
            ),
        ]),
        Paragraph("Serie diaria", estilos["Heading1"]),
        Spacer(1, .2 * cm),
        KeepTogether([
            serie_temporal(
                "Llamadas por día con desglose publicable",
                [(str(fila.get("fecha", "")), fila.get("llamadas"))
                 for fila in datos.get("serie_diaria", [])],
            ),
            Paragraph(
                "Los huecos indican días suprimidos, no cero llamadas; la línea no interpola "
                "entre ellos. El intervalo de fechas sigue siendo el declarado arriba.",
                estilos["Normal"],
            ),
        ]) if any(fila.get("llamadas") is not None
                  for fila in datos.get("serie_diaria", [])) else Paragraph(
                      "No se presenta figura diaria: no hay un desglose publicable en este corte.",
                      estilos["Normal"],
                  ),
        Spacer(1, .2 * cm),
        KeepTogether([
            serie_temporal(
                "Costo API estimado por día [USD]",
                [(str(fila.get("fecha", "")), fila.get("costo_usd"))
                 for fila in datos.get("serie_diaria", [])],
            ),
            Paragraph(
                "Sólo se representan días con al menos cinco llamadas y costo completo. "
                "Los huecos no son gasto cero; las cifras son estimaciones, no facturas.",
                estilos["Normal"],
            ),
        ]) if any(fila.get("costo_usd") is not None
                  for fila in datos.get("serie_diaria", [])) else Paragraph(
                      "No se presenta costo diario: faltan llamadas publicables o costo calculable completo.",
                      estilos["Normal"],
                  ),
        Paragraph("Distribución horaria", estilos["Heading1"]),
        Spacer(1, .2 * cm),
        KeepTogether([
            barras_horizontales(
                "Llamadas por hora local con desglose publicable",
                [(f"{int(fila.get('hora', 0)):02d}:00", fila["llamadas"])
                 for fila in datos.get("distribucion_hora_local", [])
                 if fila.get("llamadas") is not None],
            ),
            Paragraph(
                "Horas de America/Bogota en el periodo. No representan la franja tarifaria "
                "de DeepSeek ni permiten inferir el momento exacto de una clase.", estilos["Normal"],
            ),
        ]) if any(fila.get("llamadas") is not None
                  for fila in datos.get("distribucion_hora_local", [])) else Paragraph(
                      "No se presenta figura horaria: no hay un desglose publicable en este corte.",
                      estilos["Normal"],
                  ),
        Spacer(1, .5 * cm),
        Paragraph("Metodología, fuentes y límites", estilos["Heading1"]),
        Paragraph(
            "Los intervalos se interpretan en America/Bogota y se convierten a UTC para consultar "
            "los hechos. DeepSeek se estima con Decimal a partir de entrada cache hit, entrada "
            "cache miss y salida, según la tarifa vigente y la franja UTC de la llamada. La TRM "
            "se obtiene del servicio SDMX del Banco de la República por la fecha histórica de cada "
            "consumo. Las horas de mayor uso de DidaxIA no equivalen a las franjas pico del proveedor.",
            estilos["Normal"],
        ),
        Paragraph(
            "Fuentes: documentación oficial de precios y uso de tokens de DeepSeek; servicio SDMX "
            "oficial de TRM del Banco de la República. No se reconstruyen costos anteriores sin "
            "desglose y no se almacenan prompts, respuestas, llaves ni datos personales en esta tabla.",
            estilos["Normal"],
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(_texto(datos.get("regla_supresion")), estilos["ConsumoAviso"]),
        Spacer(1, 0.3 * cm),
    ]
    for advertencia in datos.get("advertencias", []):
        historia.append(Paragraph(f"• {_texto(advertencia)}", estilos["Normal"]))
    if trm.get("advertencia"):
        historia.append(Paragraph(f"TRM: {_texto(trm['advertencia'])}", estilos["ConsumoAviso"]))
    if secciones is not None:
        # El contexto y la metodología se conservan incluso en informes parciales.
        grupos = {
            "Cobertura y totales": "totales",
            "Costo estimado y conversión": "totales",
            "Desglose por proveedor y modelo": "modelos",
            "Serie diaria": "diaria",
            "Distribución horaria": "horarios",
            "Metodología, fuentes y límites": "metodologia",
        }
        seleccionados = []
        grupo = None
        for elemento in historia:
            texto = elemento.getPlainText() if isinstance(elemento, Paragraph) else None
            if texto in grupos:
                grupo = grupos[texto]
            if grupo is None or grupo in secciones:
                seleccionados.append(elemento)
        seleccionados.extend([
            Spacer(1, 0.3 * cm),
            Paragraph("Fuentes y límites del corte", estilos["Heading2"]),
            Paragraph(
                "Secciones: " + _texto(", ".join(sorted(secciones)))
                + ". Estimaciones, no facturas. Cada consumo usa su tarifa vigente y TRM histórica. "
                + "Hora de America/Bogota; la franja tarifaria es UTC. "
                + "Fuente TRM: " + _texto(trm.get("fuente")) + ". "
                + _texto(datos.get("regla_supresion"))
                + ". Las ausencias y grupos suprimidos no representan cero.",
                estilos["Normal"],
            ),
        ])
        historia = seleccionados
    documento.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return memoria.getvalue()
