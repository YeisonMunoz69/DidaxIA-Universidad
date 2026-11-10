"""Ficha individual exportable a partir del contrato ya autorizado y auditado."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from adaptadores.salientes.informes.graficas_pdf import (
    anillo_proporcion,
    es_indicador_visible,
    es_resultado_publicable,
    perfil_proporciones,
)


def _texto(valor: object) -> str:
    return escape("—" if valor is None else str(valor))


def _parrafos_cobertura(detalle: dict, estilos) -> list:
    parrafos = []
    if detalle.get("motivo_cobertura"):
        parrafos.append(Paragraph(
            f"<b>Cobertura:</b> {_texto(detalle['motivo_cobertura'])}", estilos["Normal"],
        ))
    if detalle.get("censuradas") is not None:
        parrafos.append(Paragraph(
            f"<b>Ventanas recientes excluidas:</b> {_texto(detalle['censuradas'])}.",
            estilos["Normal"],
        ))
    if detalle.get("formatos"):
        parrafos.append(Paragraph("<b>Formatos solicitados:</b> " + _texto(
            "; ".join(f"{k}: {v}" for k, v in detalle["formatos"].items())), estilos["Normal"]))
    for codigo, dato in detalle.get("por_concepto", {}).items():
        parrafos.append(Paragraph(_texto(
            f"{codigo} · {dato['nombre']}: {dato['mensajes']} mensajes candidatos"), estilos["Normal"]))
    return parrafos


def _valor_indicador(indicador, valor):
    if valor is None:
        return "sin dato"
    return f"{100 * valor:.1f} %" if indicador.get("unidad") == "proporcion" else f"{valor:.1f} puntos porcentuales"


def generar_ficha_estudiante(datos: dict) -> bytes:
    """PDF sin texto libre ni datos que no estén en la ficha de la API."""
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    documento = SimpleDocTemplate(
        salida, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.7 * cm, bottomMargin=1.7 * cm,
        title="Ficha de actividad individual · DidaxIA", author="DidaxIA",
        invariant=1,
    )
    periodo = datos.get("periodo", {})
    estudiante = datos.get("estudiante", {})
    actividad = datos.get("actividad", {})
    kpi = [item for item in [
        *datos.get("indicadores_actividad", []),
        *datos.get("indicios_conductuales", {}).get("observables", []),
    ] if es_resultado_publicable(item)]
    historia = [
        Paragraph("DidaxIA · Ficha de actividad individual", estilos["Title"]),
        Paragraph(_texto(estudiante.get("nombre", "Estudiante")), estilos["Heading2"]),
        Paragraph(
            f"Instrumento-Prototipo · Periodo: {_texto(periodo.get('desde'))} "
            f"a {_texto(periodo.get('hasta'))} (extremo final exclusivo).",
            estilos["Normal"],
        ),
        Spacer(1, .35 * cm),
        Paragraph("Actividad observada", estilos["Heading2"]),
    ]
    filas = [["Turnos", "Conversaciones", "Días activos", "Sin fuente"]]
    filas.append([
        _texto(actividad.get("turnos_registrados")),
        _texto(actividad.get("conversaciones")),
        _texto(actividad.get("dias_con_actividad")),
        _texto(datos.get("respuesta", {}).get("sin_fuente")),
    ])
    tabla = Table(filas, colWidths=[4.0 * cm] * 4)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    historia.extend((tabla, Spacer(1, .4 * cm)))
    from adaptadores.salientes.informes.explicacion_factores import (
        explicar_factores,  # noqa: PLC0415
    )

    historia.extend(explicar_factores([*kpi, *datos.get("indicadores_anteproyecto", [])], estilos))
    if kpi:
        historia.append(Paragraph("KPI calculados", estilos["Heading2"]))
    figura = perfil_proporciones("Valores publicados · escala 0–100 %", kpi)
    if figura is not None:
        historia.extend((figura, Spacer(1, .2 * cm)))
    if kpi:
        historia.append(Paragraph(
            "Cada barra usa la población propia de su KPI y no es una calificación.", estilos["Normal"],
        ))
    historia.extend(_seccion_anteproyecto(
        [item for item in datos.get("indicadores_anteproyecto", []) if es_indicador_visible(item)],
        estilos,
    ))
    for item in kpi:
        valor = item.get("valor")
        visible = f"{100 * valor:.1f} %" if valor is not None and item.get("unidad") == "proporcion" else _texto(valor)
        bloque = [
            Spacer(1, .25 * cm),
            Paragraph(_texto(item.get("nombre")), estilos["Heading3"]),
            Paragraph(
                f"<b>Estado:</b> {_texto(item.get('estado'))} · "
                f"<b>Valor:</b> {visible} · <b>Muestra:</b> {_texto(item.get('muestra'))} · "
                f"<b>Numerador:</b> {_texto(item.get('numerador'))} · "
                f"<b>Denominador:</b> {_texto(item.get('denominador'))}",
                estilos["Normal"],
            ),
            Paragraph(_texto(item.get("interpretacion")), estilos["Normal"]),
            Paragraph(
                f"<b>Qué mide:</b> {_texto(item.get('definicion_operacional'))}",
                estilos["Normal"],
            ),
        ]
        metodo = item.get("metodologia") or {}
        if metodo:
            bloque.append(Paragraph(
                f"<b>Fórmula:</b> {_texto(metodo.get('formula'))}. "
                f"<b>Ejemplo:</b> {_texto(metodo.get('ejemplo'))}", estilos["Normal"],
            ))
            simbolos = metodo.get("simbolos") or {}
            if simbolos:
                bloque.append(Paragraph(
                    "<b>Símbolos:</b> " + "; ".join(
                        f"{_texto(simbolo)} = {_texto(significado)}"
                        for simbolo, significado in simbolos.items()
                    ) + ".", estilos["Normal"],
                ))
            bloque.append(Paragraph(
                f"<b>Valores altos:</b> {_texto(metodo.get('alto'))} "
                f"<b>Valores bajos:</b> {_texto(metodo.get('bajo'))} "
                f"<b>Ausencia:</b> {_texto(metodo.get('ausente'))}", estilos["Normal"],
            ))
            bloque.append(Paragraph(
                f"<b>Incertidumbre:</b> {_texto(metodo.get('incertidumbre'))}",
                estilos["Normal"],
            ))
        bloque.append(Paragraph(
            f"<b>Fuentes:</b> {_texto(', '.join(item.get('fuentes', [])))}. "
            f"<b>Faltantes:</b> {_texto(item.get('faltantes'))}. "
            f"<b>Unidad:</b> {_texto(item.get('unidad'))}. "
            f"<b>Población:</b> {_texto(item.get('poblacion_elegible'))}.",
            estilos["Normal"],
        ))
        bloque.extend(_parrafos_cobertura(item.get("detalle", {}), estilos))
        for limite in item.get("limitaciones", []):
            bloque.append(Paragraph(f"Límite: {_texto(limite)}", estilos["Normal"]))
        historia.append(KeepTogether(bloque))
    indicios = datos.get("indicios_conductuales", {})
    historia.extend(_parrafos_cobertura({"motivo_cobertura": indicios.get("motivo")}, estilos))
    componentes = [item for item in indicios.get("componentes", [])
                   if es_resultado_publicable(item)]
    if indicios.get("estado") != "no_habilitado" and componentes:
        historia.extend((Spacer(1, .3 * cm), Paragraph("Indicios del lenguaje", estilos["Heading2"])))
        historia.append(Paragraph(
            "Frecuencias de mensajes con patrones reconocidos; no son diagnóstico "
            "ni los constructos conductuales pendientes.", estilos["Normal"],
        ))
        for componente in componentes:
            valor = componente.get("valor")
            historia.append(Paragraph(
                f"{_texto(componente.get('nombre'))}: "
                f"{'sin dato' if valor is None else f'{100 * valor:.1f} %'} · "
                f"{_texto(componente.get('numerador'))} de "
                f"{_texto(componente.get('denominador'))} mensajes.", estilos["Normal"],
            ))
    documento.build(historia)
    return salida.getvalue()


def _seccion_anteproyecto(indicadores: list[dict], estilos) -> list:
    if not indicadores:
        return []
    seccion = [
        PageBreak(),
        Paragraph("Fenómenos e indicadores observables del diálogo · Instrumento-Prototipo", estilos["Heading2"]),
        Paragraph(
            "Cada medida conserva su propio denominador: mensajes, sondeos o intentos. "
            "El contraste temporal se expresa en puntos porcentuales. Los valores describen "
            "evidencia registrada y no diagnostican estados internos ni aprendizaje.", estilos["Normal"],
        ),
    ]
    figura = perfil_proporciones("Indicios observados · escala 0–100 %", indicadores)
    if figura is not None:
        seccion.extend((figura, Spacer(1, .15 * cm)))
    primero = next((item for item in indicadores
                    if es_resultado_publicable(item) and isinstance(item.get("numerador"), (int, float))
                    and isinstance(item.get("denominador"), (int, float))
                    and item["denominador"] > 0
                    and 0 <= item["numerador"] <= item["denominador"]), None)
    if primero is not None:
        seccion.extend((
            Paragraph(f"Detalle de {_texto(primero.get('nombre'))}", estilos["Heading3"]),
            anillo_proporcion(float(primero["numerador"]), float(primero["denominador"])),
            Spacer(1, .15 * cm),
        ))
    for indicador in indicadores:
        valor = indicador.get("valor") if es_resultado_publicable(indicador) else None
        metodo = indicador.get("metodologia") or {}
        bloque = [
            Paragraph(
                f"<b>{_texto(indicador.get('nombre'))}:</b> "
                f"{_valor_indicador(indicador, valor)} · "
                f"Estado: {_texto(indicador.get('estado'))} · "
                f"{_texto(indicador.get('numerador'))} de "
                f"{_texto(indicador.get('denominador'))} oportunidades.", estilos["Normal"],
            ),
            Paragraph(
                f"<b>Fórmula:</b> {_texto(metodo.get('formula'))}. "
                f"<b>Ejemplo:</b> {_texto(metodo.get('ejemplo'))} "
                f"<b>Límite:</b> {_texto(metodo.get('incertidumbre'))}", estilos["Normal"],
            ),
            Paragraph(
                f"<b>Alto:</b> {_texto(metodo.get('alto'))} "
                f"<b>Bajo:</b> {_texto(metodo.get('bajo'))} "
                f"<b>Ausente:</b> {_texto(metodo.get('ausente'))} "
                f"<b>Fuente:</b> {_texto(', '.join(indicador.get('fuentes', [])))}.",
                estilos["Normal"],
            ),
            Spacer(1, .18 * cm),
        ]
        detalle = indicador.get("detalle") or {}
        bloque[-1:-1] = _parrafos_cobertura(detalle, estilos)
        if detalle.get("trazas_faltantes"):
            bloque.insert(-1, Paragraph(
                f"<b>Trazas no legibles excluidas:</b> {_texto(detalle['trazas_faltantes'])}.",
                estilos["Normal"],
            ))
        if detalle.get("por_concepcion"):
            etiquetas = ", ".join(f"{codigo}: {cantidad}"
                                  for codigo, cantidad in detalle["por_concepcion"].items())
            bloque.insert(-1, Paragraph(
                f"<b>Etiquetas observadas:</b> {_texto(etiquetas)}.", estilos["Normal"],
            ))
        seccion.append(KeepTogether(bloque))
    seccion.append(PageBreak())
    return seccion
