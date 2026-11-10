"""Generación determinista del informe institucional de KPI."""

from __future__ import annotations

import json
from decimal import Decimal
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
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from adaptadores.salientes.informes.graficas_pdf import (
    anillo_proporcion,
    barras_horizontales,
    es_indicador_visible,
    intervalo_cuartiles,
    mosaico_proporcion,
    perfil_proporciones,
)

VERSION_PLANTILLA = "informe-kpi-1.6"


def _canonico(valor: object) -> object:
    """Normaliza colecciones sin significado posicional antes de presentarlas."""
    if isinstance(valor, dict):
        return {
            str(clave): ([_canonico(item) for item in valor[clave]]
                         if clave == "items" and isinstance(valor[clave], (list, tuple))
                         else _canonico(valor[clave]))
            for clave in sorted(valor, key=str)
        }
    if isinstance(valor, (list, tuple, set, frozenset)):
        elementos = [_canonico(item) for item in valor]
        return sorted(
            elementos,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str),
        )
    return valor


def _fuentes() -> tuple[str, str]:
    import reportlab  # noqa: PLC0415

    raiz = Path(reportlab.__file__).resolve().parent / "fonts"
    normal, negrita = raiz / "Vera.ttf", raiz / "VeraBd.ttf"
    if normal.is_file() and negrita.is_file():
        if "DidaxIA" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DidaxIA", normal))
            pdfmetrics.registerFont(TTFont("DidaxIA-Bold", negrita))
        return "DidaxIA", "DidaxIA-Bold"
    return "Helvetica", "Helvetica-Bold"


def _estilos():
    normal, negrita = _fuentes()
    base = getSampleStyleSheet()
    base["Normal"].fontName = normal
    base["Normal"].fontSize = 8.5
    base["Normal"].leading = 12
    for nombre in ("Title", "Heading1", "Heading2", "Heading3"):
        base[nombre].fontName = negrita
        base[nombre].textColor = colors.black
    base["Title"].fontSize = 24
    base["Title"].leading = 29
    base["Heading2"].keepWithNext = 1
    base.add(ParagraphStyle(
        name="Portada", parent=base["Normal"], alignment=TA_CENTER,
        fontSize=11, leading=16, textColor=colors.black,
    ))
    base.add(ParagraphStyle(
        name="Aviso", parent=base["Normal"], borderColor=colors.black,
        borderWidth=.5, borderPadding=7, backColor=colors.white,
        spaceBefore=10, spaceAfter=10,
    ))
    return base, normal, negrita


def _pie(canvas, doc) -> None:
    canvas.saveState()
    normal, _ = _fuentes()
    canvas.setFont(normal, 7)
    canvas.setFillColor(colors.black)
    canvas.drawString(1.7 * cm, 1.05 * cm, f"DidaxIA · {VERSION_PLANTILLA}")
    canvas.drawRightString(A4[0] - 1.7 * cm, 1.05 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _tabla(filas, anchos=None) -> Table:
    normal, negrita = _fuentes()
    estilo_celda = ParagraphStyle(
        "CeldaInforme", fontName=normal, fontSize=7.4, leading=9.5,
        textColor=colors.black, wordWrap="LTR", splitLongWords=True,
    )
    estilo_cabecera = ParagraphStyle(
        "CabeceraTablaInforme", parent=estilo_celda, fontName=negrita,
        textColor=colors.black,
    )
    preparadas = []
    for indice, fila in enumerate(filas):
        estilo = estilo_cabecera if indice == 0 else estilo_celda
        preparadas.append([
            celda if hasattr(celda, "wrap") else Paragraph(
                _seguro(celda).replace("\n", "<br/>"), estilo
            )
            for celda in fila
        ])
    tabla = Table(preparadas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C9C9C9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _tabla_ficha(filas) -> Table:
    """Campos explicativos en dos columnas, legibles incluso al partir página."""
    normal, negrita = _fuentes()
    etiqueta = ParagraphStyle(
        "EtiquetaFichaKPI", fontName=negrita, fontSize=7.5, leading=10,
        textColor=colors.black, wordWrap="LTR",
    )
    valor = ParagraphStyle(
        "ValorFichaKPI", fontName=normal, fontSize=7.8, leading=10.8,
        textColor=colors.black, wordWrap="LTR", splitLongWords=True,
    )
    preparadas = [
        [Paragraph(_seguro(nombre), etiqueta), Paragraph(_seguro(contenido), valor)]
        for nombre, contenido in filas
    ]
    tabla = Table(preparadas, colWidths=[4.15 * cm, 12.15 * cm], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), .45, colors.HexColor("#B8B8B8")),
        ("INNERGRID", (0, 0), (-1, -1), .25, colors.HexColor("#D5D5D5")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEEEEE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla


def _tabla_catalogo(indicadores) -> LongTable:
    """Catálogo multipágina con código ancho y cabecera repetida."""
    normal, negrita = _fuentes()
    celda = ParagraphStyle(
        "CeldaCatalogoKPI", fontName=normal, fontSize=6.7, leading=8.6,
        textColor=colors.black, wordWrap="LTR", splitLongWords=True,
    )
    cabecera = ParagraphStyle(
        "CabeceraCatalogoKPI", parent=celda, fontName=negrita, textColor=colors.black,
    )
    filas = [[Paragraph(texto, cabecera) for texto in (
        "Código", "Dimensión", "Estado", "Madurez", "Unidad"
    )]]
    for item in indicadores:
        filas.append([
            Paragraph(_seguro(item.get("codigo", "")), celda),
            Paragraph(_seguro(item.get("dimension", "")), celda),
            Paragraph(_seguro(item.get("estado", "")), celda),
            Paragraph(_seguro(item.get("madurez_metodologica", "")), celda),
            Paragraph(_seguro(item.get("unidad", "")), celda),
        ])
    tabla = LongTable(
        filas, colWidths=[5.65 * cm, 2.45 * cm, 3.25 * cm, 3.0 * cm, 1.95 * cm],
        repeatRows=1, hAlign="LEFT",
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E9E9")),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#C9C9C9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _grafica_productores(datos: dict):
    cobertura = datos.get("calidad", {}).get("telemetria", {}).get(
        "cobertura_por_productor", []
    )
    observados = sum(1 for item in cobertura if item.get("observado"))
    pendientes = max(0, len(cobertura) - observados)
    if not cobertura:
        return barras_horizontales("Cobertura real de productores", [])
    return barras_horizontales("Cobertura real de productores", [
        ("Con eventos observados", observados),
        ("Sin eventos en el periodo", pendientes),
    ])


def _visible(valor: object) -> str:
    """Ausencia visible, nunca la representación técnica ``None``."""
    if valor is None or valor == "":
        return "—"
    normalizado = _canonico(valor)
    if isinstance(normalizado, (dict, list)):
        return json.dumps(normalizado, ensure_ascii=False, sort_keys=True)
    return str(normalizado)


def _seguro(valor: object) -> str:
    """Texto escapado sin marcas Markdown que ReportLab no interpreta."""
    return escape(_visible(valor).replace("**", "").replace("`", ""))


def _seleccionar(datos: dict, tipo: str, codigo: str) -> list[dict]:
    indicadores = sorted(
        (_canonico(item) for item in datos.get("indicadores", [])),
        key=lambda item: str(item.get("codigo", "")),
    )
    if tipo == "indicador":
        indicadores = [item for item in indicadores if item.get("codigo") == codigo]
        if not indicadores:
            raise ValueError("el indicador solicitado no aparece en el resultado")
    elif tipo not in {"completo", "seleccion"}:
        raise ValueError("tipo de informe desconocido")
    indicadores = [item for item in indicadores if es_indicador_visible(item)]
    if not indicadores:
        raise ValueError("el informe no contiene indicadores con valor en este periodo")
    return indicadores


def _composicion(item: dict, estilos) -> list:
    if item.get("estado") != "disponible":
        return []
    numerador, denominador = item.get("numerador"), item.get("denominador")
    validos = all(isinstance(numero, (int, float, Decimal)) and not isinstance(numero, bool)
                  for numero in (numerador, denominador))
    if not validos or denominador <= 0 or not 0 <= numerador <= denominador:
        return []
    figura = (anillo_proporcion(float(numerador), float(denominador))
              if item.get("dimension") in {"conductual", "aprendizaje"}
              else mosaico_proporcion(float(numerador), float(denominador)))
    return [KeepTogether([
        Paragraph("Composición del denominador observado", estilos["Heading2"]),
        figura,
        Paragraph(
            "Muestra la parte observada y el resto del denominador de esta ficha. "
            "No indica aprendizaje ni mejora; consulte la definición y los faltantes.",
            estilos["Normal"],
        ),
        Spacer(1, .2 * cm),
    ])]


def _distribucion_observada(item: dict) -> list:
    if item.get("estado") != "disponible" or item.get("valor") is None:
        return []
    dibujo = intervalo_cuartiles(item.get("detalle", {}), item["valor"], item.get("unidad", ""))
    return [dibujo, Spacer(1, .2 * cm)] if dibujo is not None else []


def _metodologia(item: dict, estilos) -> list:
    """Mismo contrato pedagógico que el diálogo; sin mostrar LaTeX crudo."""
    metodo = item.get("metodologia")
    if not metodo:
        return []
    bloques = [Paragraph("Cómo se calcula y qué significa", estilos["Heading2"])]
    for titulo, contenido in (
        ("Pregunta", metodo["pregunta"]),
        ("Fórmula", metodo["formula"]),
        ("Símbolos", "; ".join(f"{k}: {v}" for k, v in metodo["simbolos"].items())),
        ("Agregación", metodo["regla_agregacion"]),
        ("Ejemplo ilustrativo", metodo["ejemplo"]),
        ("Valores altos", metodo["alto"]),
        ("Valores bajos", metodo["bajo"]),
        ("Valores ausentes", metodo["ausente"]),
        ("Incertidumbre", metodo["incertidumbre"]),
        ("Recolección", metodo["recoleccion"]),
    ):
        bloques.append(Paragraph(f"<b>{titulo}.</b> {_seguro(contenido)}", estilos["Normal"]))
        bloques.append(Spacer(1, .12 * cm))
    if metodo.get("items"):
        bloques.append(Paragraph("Ítems preliminares: " + _seguro("; ".join(metodo["items"])), estilos["Normal"]))
        bloques.append(Paragraph(_seguro(metodo.get("escala_respuesta", "")), estilos["Normal"]))
    if metodo.get("prototipo"):
        bloques.append(Paragraph(_seguro(metodo["fundamento"]), estilos["Aviso"]))
    return bloques


def _panorama_observado(indicadores: list[dict], tipo: str, estilos) -> list:
    if tipo not in {"completo", "seleccion"}:
        return []
    graficas = []
    for dimension in dict.fromkeys(item.get("dimension") for item in indicadores):
        figura = perfil_proporciones(
            f"{str(dimension).capitalize()} · KPI con valor observado",
            [item for item in indicadores if item.get("dimension") == dimension],
        )
        if figura is not None:
            graficas.extend((figura, Spacer(1, .18 * cm)))
    if not graficas:
        return []
    return [
        Paragraph("Panorama de proporciones observadas", estilos["Heading2"]),
        Paragraph(
            "Cada barra representa una fracción calculada con la muestra indicada. "
            "Las definiciones y poblaciones cambian entre KPI: su longitud no es "
            "un ranking de aprendizaje ni de calidad. Las medidas sin valor se "
            "conservan en sus fichas sin dibujarlas como cero.", estilos["Normal"],
        ),
        Spacer(1, .24 * cm),
        *graficas,
        Spacer(1, .25 * cm),
    ]


def generar_informe_kpi(datos: dict, *, tipo: str, codigo: str = "") -> bytes:
    """Crea un PDF autosuficiente desde el contrato explicable de KPI."""
    estilos, _, _ = _estilos()
    indicadores = _seleccionar(datos, tipo, codigo)

    memoria = BytesIO()
    documento = BaseDocTemplate(
        memoria, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.55 * cm, bottomMargin=1.55 * cm,
        title="Informe institucional DidaxIA", author="DidaxIA",
        invariant=1,
    )
    marco = Frame(documento.leftMargin, documento.bottomMargin, documento.width, documento.height)
    documento.addPageTemplates(PageTemplate(id="informe", frames=[marco], onPage=_pie))
    historia = [Spacer(1, 3.2 * cm), Paragraph("DidaxIA", estilos["Portada"]),
                Paragraph("Informe institucional de indicadores", estilos["Title"]),
                Spacer(1, .5 * cm)]
    periodo = datos.get("periodo", {})
    historia.extend([
        Paragraph(
            f"{('Informe completo' if tipo == 'completo' else 'Informe seleccionado' if tipo == 'seleccion' else 'Informe individual')} · "
            f"catálogo {datos.get('version_catalogo', '—')} · definiciones "
            f"{datos.get('version_definiciones', '—')}", estilos["Portada"]),
        Paragraph(
            f"Periodo semiabierto: [{periodo.get('desde', '—')}, {periodo.get('hasta', '—')}) · "
            "America/Bogota", estilos["Portada"]),
        Spacer(1, 1.3 * cm),
        Paragraph(
            "Estos indicadores son señales descriptivas para evaluación y supervisión. "
            "No constituyen diagnóstico clínico, no demuestran causalidad y deben "
            "interpretarse junto con muestra, cobertura, periodo y limitaciones.",
            estilos["Aviso"]),
        Paragraph("Instrumento-Prototipo · Reglas documentadas y probadas; las propuestas preliminares aún requieren contraste externo y calibración.", estilos["Aviso"]),
        PageBreak(),
        Paragraph("Metodología y alcance", estilos["Heading1"]),
        Paragraph(
            "Los cálculos usan la población elegible declarada por matrícula histórica, "
            "excluyen el contexto de consulta profesional y conservan las ausencias como "
            "ausencias. Cada definición aporta fórmula, numerador, denominador, muestra, "
            "fuentes, interpretación determinista y limitaciones.", estilos["Normal"]),
        Spacer(1, .25 * cm),
        _tabla([
            ["Campo", "Valor"],
            ["Alcance", str(datos.get("alcance", "—"))],
            ["Filtros", ", ".join(
                f"{k}={_visible(v)}" for k, v in sorted(datos.get("filtros", {}).items())
            ) or "Ninguno"],
            ["Estudiantes elegibles", str(datos.get("poblacion", {}).get("estudiantes_elegibles", "—"))],
            ["Clases", str(datos.get("poblacion", {}).get("clases", "—"))],
            ["Instante explícito del corte", _visible(datos.get("corte", {}).get("instante"))],
            ["Secuencia del corte", _visible(datos.get("corte", {}).get("secuencia"))],
            ["Corpus observados", ", ".join(sorted(datos.get("versiones_observadas", {}).get("corpus", []))) or "No consta"],
            ["Modelos observados", ", ".join(sorted(datos.get("versiones_observadas", {}).get("modelos", []))) or "No consta"],
        ], [4.2 * cm, 12.1 * cm]),
        Spacer(1, .4 * cm),
        barras_horizontales(
            "Indicadores incluidos por dimensión",
            [(dimension, sum(str(item.get("dimension", "sin dimensión")) == dimension
                             for item in indicadores))
             for dimension in sorted({str(item.get("dimension", "sin dimensión"))
                                      for item in indicadores})],
        ),
        Paragraph(
            "Es un recuento de fichas por dimensión, no una medida de logro en esas áreas.",
            estilos["Normal"],
        ),
        Spacer(1, .2 * cm),
        _grafica_productores(datos),
        Paragraph(
            "Productor observado significa que emitió al menos un evento en el periodo; "
            "no demuestra cobertura completa ni ausencia de errores.", estilos["Normal"],
        ),
        PageBreak(),
        Paragraph("Resultados", estilos["Heading1"]),
    ])
    from adaptadores.salientes.informes.explicacion_factores import (
        explicar_factores,  # noqa: PLC0415
    )

    historia.extend(explicar_factores(indicadores, estilos))
    historia.extend(_panorama_observado(indicadores, tipo, estilos))
    def grupo_de(item: dict) -> str:
        if item.get("madurez_metodologica") in {"experimental", "en_calibracion"}:
            return "experimentales"
        return "operacionales"

    titulos_de_grupo = {
        "operacionales": "Indicadores operacionales o validados",
        "experimentales": "Indicadores experimentales",
    }
    explicaciones_de_grupo = {
        "operacionales": "Valores publicados con su fórmula, población, periodo y muestra.",
        "experimentales": (
            "Valores técnicamente calculables cuya regla aún no tiene calibración externa. "
            "No se mezclan silenciosamente con los indicadores operacionales."
        ),
    }
    if tipo in {"completo", "seleccion"}:
        conteos_grupo = {
            grupo: sum(grupo_de(item) == grupo for item in indicadores)
            for grupo in titulos_de_grupo
        }
        historia.extend([
            _tabla([
                ["Grupo", "Cantidad"],
                ["Operacionales o validados", conteos_grupo["operacionales"]],
                ["Experimentales", conteos_grupo["experimentales"]],
            ], [12.1 * cm, 4.2 * cm]),
            Spacer(1, .35 * cm),
        ])
        indicadores = sorted(indicadores, key=lambda item: (
            ("operacionales", "experimentales").index(grupo_de(item)),
            str(item.get("codigo", "")),
        ))

    total_indicadores = len(indicadores)
    grupo_anterior = None
    for indice, item in enumerate(indicadores, start=1):
        grupo = grupo_de(item)
        if tipo in {"completo", "seleccion"} and grupo != grupo_anterior:
            if grupo_anterior is not None:
                historia.append(PageBreak())
            historia.extend([
                Paragraph(titulos_de_grupo[grupo], estilos["Heading1"]),
                Paragraph(explicaciones_de_grupo[grupo], estilos["Aviso"]),
                Spacer(1, .2 * cm),
            ])
            grupo_anterior = grupo
        elif indice > 1:
            historia.append(PageBreak())
        valor = item.get("valor")
        valor_texto = "Sin valor publicado" if valor is None else str(valor)
        muestra = item.get("muestra", 0)
        titulo_y_resumen = [
            Paragraph(
                f"FICHA {indice} DE {total_indicadores}",
                ParagraphStyle(
                    f"SobrelineaFicha{indice}", parent=estilos["Normal"],
                    fontSize=7, leading=9, textColor=colors.black,
                    spaceAfter=3,
                ),
            ),
            Paragraph(
                _seguro(f"{item.get('codigo', '—')} · {item.get('nombre', '')}"),
                estilos["Heading2"],
            ),
            _tabla([
                ["Dimensión", "Estado", "Madurez", "Valor", "Muestra"],
                [_visible(item.get("dimension")), _visible(item.get("estado")),
                 _visible(item.get("madurez_metodologica")), valor_texto,
                 str(muestra),
                ],
            ], [2.7 * cm, 3.1 * cm, 3.5 * cm, 4.0 * cm, 3.0 * cm]),
        ]
        historia.extend([
            KeepTogether(titulo_y_resumen),
            Spacer(1, .2 * cm),
        ])
        historia.extend(_composicion(item, estilos))
        historia.extend(_distribucion_observada(item))
        historia.extend(_metodologia(item, estilos))
        historia.extend([
            _tabla_ficha([
                ("Definición operacional", item.get("definicion_operacional")),
                ("Fórmula", item.get("formula")),
                ("Unidad", item.get("unidad")),
                ("Faltantes registrados", item.get("faltantes")),
                ("Muestra mínima", item.get("muestra_minima")),
                ("Seguimiento truncado", item.get("detalle", {}).get("censuradas")),
                ("Trazas no legibles", item.get("detalle", {}).get("trazas_faltantes")),
                ("Cobertura de la observación", item.get("detalle", {}).get("motivo_cobertura")),
                ("Concepciones observadas", item.get("detalle", {}).get("por_concepcion")),
                ("Afirmaciones conceptuales candidatas", item.get("detalle", {}).get("por_concepto")),
                ("Formatos de ayuda solicitados", item.get("detalle", {}).get("formatos")),
                ("Formatos más solicitados", item.get("detalle", {}).get("formatos_modales")),
                ("Episodios recientes excluidos", item.get("detalle", {}).get("episodios_recientes_excluidos")),
                ("Personas sin par temporal", item.get("detalle", {}).get("sin_par")),
                ("Numerador observado", item.get("numerador")),
                ("Denominador observado", item.get("denominador")),
                ("Definición del numerador", item.get("definicion_numerador")),
                ("Definición del denominador", item.get("definicion_denominador")),
                ("Población elegible", item.get("poblacion_elegible")),
                ("Fuentes", ", ".join(item.get("fuentes", [])) or "No instrumentado"),
                ("Estado técnico", item.get("estado_tecnico")),
                ("Madurez metodológica", item.get("madurez_metodologica")),
                ("Periodo", item.get("periodo") or periodo),
                ("Filtros", item.get("filtros") or datos.get("filtros", {})),
                ("Versión de interpretación", item.get("version_interpretacion")),
                ("Versiones de corpus", item.get("version_corpus") or ", ".join(item.get("versiones_corpus", [])) or "No consta"),
                ("Versiones de modelo", item.get("version_modelo") or ", ".join(item.get("versiones_modelo", [])) or "No consta"),
                ("Advertencias", "; ".join(sorted(item.get("advertencias", []))) or "Ninguna adicional declarada"),
                ("Dato faltante o motivo de no cálculo", item.get("falta") or item.get("motivo_no_calculo")),
                ("Interpretación", item.get("interpretacion")),
                ("Limitaciones", "; ".join(sorted(item.get("limitaciones", []))) or "Ninguna adicional declarada"),
            ]),
            Spacer(1, .3 * cm),
        ])
    calidad = datos.get("calidad", {})
    instrumentos = calidad.get("instrumentos_prototipo")
    historia.extend([
        PageBreak(), Paragraph("Calidad, límites y catálogo", estilos["Heading1"]),
        Paragraph(
            "La calidad se presenta sin sustituir ausencias por cero. Los umbrales de "
            "muestra son reglas metodológicas de publicación y no una política de anonimato.",
            estilos["Normal"]),
        _tabla([
            ["Aspecto", "Detalle"],
            ["Resultados incluidos", f"{len(indicadores)} con valor publicado"],
            ["Perfiles incompletos", str(calidad.get("perfiles", {}).get("incompletos", "—"))],
            ["Eventos", str(calidad.get("telemetria", {}).get("eventos", "—"))],
            ["Periodos con observación baja", str(calidad.get("telemetria", {}).get("periodos_observacion_baja", []))],
            ["Duplicados", str(calidad.get("telemetria", {}).get("duplicados", "—"))],
            ["Conflictos de idempotencia", str(calidad.get("telemetria", {}).get("conflictos_idempotencia", "—"))],
            ["Eventos incompatibles", str(calidad.get("telemetria", {}).get("eventos_incompatibles", "—"))],
            ["Cobertura por productor", str(calidad.get("telemetria", {}).get("cobertura_por_productor", []))],
            ["Faltantes por campo", str(calidad.get("perfiles", {}).get("faltantes_por_campo", {}))],
            ["Reglas de supresión", str(calidad.get("reglas", {}).get("supresion", {}))],
            ["Plantilla", VERSION_PLANTILLA],
        ], [5.2 * cm, 11.1 * cm]),
        Spacer(1, .4 * cm),
    ])
    if instrumentos is not None:
        historia.extend([
            Paragraph("Cobertura de los instrumentos prototipo", estilos["Heading2"]),
            Paragraph(
                "Son conteos de oportunidades observadas, no puntuaciones de los "
                "constructos. El sondeo y la corrección pueden ocurrir en turnos "
                "distintos; sin denominador, el KPI permanece sin dato.",
                estilos["Normal"],
            ),
            _tabla([
                ["Oportunidad observada", "Turnos o mensajes"],
                ["Mensajes analizables PS-Anx", str(instrumentos.get("mensajes_analizables_ps_anx", "—"))],
                ["Trazas referenciadas / legibles / faltantes", " / ".join(
                    str(instrumentos.get(clave, "—")) for clave in (
                        "trazas_referenciadas", "trazas_legibles", "trazas_faltantes"
                    ))],
                ["Sondeos ofrecidos / clasificados", " / ".join(
                    str(instrumentos.get(clave, "—")) for clave in (
                        "sondeos_ofrecidos", "sondeos_clasificados"
                    ))],
                ["Intentos verificables / correcciones / reintentos", " / ".join(
                    str(instrumentos.get(clave, "—")) for clave in (
                        "intentos_verificables", "correcciones_candidatas", "reintentos_observados"
                    ))],
            ], [11.3 * cm, 5 * cm]),
            Spacer(1, .4 * cm),
        ])
    historia.extend([
        Paragraph("Catálogo incluido", estilos["Heading2"]),
        _tabla_catalogo(indicadores),
    ])
    documento.build(historia)
    return memoria.getvalue()
