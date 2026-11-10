"""Informe determinista del corte institucional de auditoría."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

from adaptadores.salientes.informes.graficas_pdf import barras_horizontales, lollipop_horizontal
from adaptadores.salientes.informes.pdf_kpi import _estilos, _seguro, _tabla, _visible

VERSION_PLANTILLA_AUDITORIA = "informe-auditoria-1.1"


def _pie(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.black)
    canvas.drawString(1.7 * cm, 1.05 * cm, f"DidaxIA · {VERSION_PLANTILLA_AUDITORIA}")
    canvas.drawRightString(A4[0] - 1.7 * cm, 1.05 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _persona(detalle: dict | None) -> str:
    detalle = detalle or {}
    identidad = detalle.get("etiqueta") or detalle.get("nombre") or detalle.get("identificador")
    partes = [identidad, detalle.get("correo")]
    if detalle.get("identificador") and detalle.get("identificador") != identidad:
        partes.append(f"ID: {detalle['identificador']}")
    roles = detalle.get("roles") or []
    if roles:
        partes.append(f"Roles {detalle.get('naturaleza_roles', 'actuales')}: {', '.join(sorted(roles))}")
    ubicacion = " · ".join(
        str(detalle.get(campo)) for campo in ("facultad", "programa") if detalle.get(campo)
    )
    if ubicacion:
        partes.append(ubicacion)
    return " · ".join(str(parte) for parte in partes if parte)


def generar_informe_auditoria(datos: dict) -> bytes:
    """Genera el corte explícito; nunca consulta el reloj ni la base."""
    estilos, _, _ = _estilos()
    memoria = BytesIO()
    documento = BaseDocTemplate(
        memoria,
        pagesize=A4,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.55 * cm,
        title="Informe de auditoría institucional",
        author="DidaxIA",
        invariant=1,
    )
    marco = Frame(documento.leftMargin, documento.bottomMargin, documento.width, documento.height)
    documento.addPageTemplates(PageTemplate(id="auditoria", frames=[marco], onPage=_pie))

    resumen = datos.get("resumen", {})
    filtros = datos.get("filtros", {})
    operaciones = sorted(datos.get("operaciones", []), key=lambda item: int(item.get("id", 0)))
    historia = [
        Spacer(1, 2.8 * cm),
        Paragraph("DidaxIA", estilos["Portada"]),
        Paragraph("Informe de auditoría institucional", estilos["Title"]),
        Spacer(1, .4 * cm),
        Paragraph(_seguro(datos.get("institucion") or "Institución universitaria"), estilos["Portada"]),
        Paragraph(
            f"Corte previo a la descarga · secuencia máxima {_seguro(datos.get('corte_secuencia'))} · "
            f"{_seguro(datos.get('corte_instante'))} · America/Bogota",
            estilos["Portada"],
        ),
        Spacer(1, .8 * cm),
        _tabla([
            ["Campo", "Valor"],
            ["Solicitado por", _persona(datos.get("solicitante"))],
            ["Periodo cubierto", f"{_visible(resumen.get('desde'))} a {_visible(resumen.get('hasta'))}"],
            ["Filtros", _visible(filtros) if any(filtros.values()) else "Sin filtros"],
            ["Operaciones incluidas", resumen.get("total", len(operaciones))],
            ["Versión de plantilla", VERSION_PLANTILLA_AUDITORIA],
        ], [4.5 * cm, 11.8 * cm]),
        Spacer(1, .6 * cm),
        Paragraph(
            "Este documento explica quién ejecutó una operación institucional, sobre quién o qué, "
            "cuándo ocurrió y qué cambió. No es un registro de actividad académica ni contiene "
            "textos de conversación.",
            estilos["Aviso"],
        ),
        PageBreak(),
        Paragraph("Resumen del corte", estilos["Heading1"]),
        _tabla([
            ["Indicador", "Cantidad"],
            ["Operaciones", resumen.get("total", 0)],
            ["Actores", resumen.get("actores", 0)],
            ["Operaciones sensibles", resumen.get("sensibles", 0)],
            ["Con doble aprobación", resumen.get("doble_aprobacion", 0)],
        ], [7.5 * cm, 8.8 * cm]),
        Spacer(1, .45 * cm),
        Paragraph("Cantidades por categoría", estilos["Heading2"]),
        _tabla(
            [["Categoría", "Cantidad"]]
            + [[clave, valor] for clave, valor in sorted(resumen.get("por_categoria", {}).items())],
            [10.8 * cm, 5.5 * cm],
        ),
        Spacer(1, .25 * cm),
        barras_horizontales(
            "Operaciones por categoría",
            list(sorted(resumen.get("por_categoria", {}).items())),
        ),
        Paragraph(
            "Cada barra representa operaciones registradas en el corte, no personas ni gravedad. "
            "Las categorías con cero eventos no prueban ausencia de riesgo.", estilos["Normal"],
        ),
        Spacer(1, .45 * cm),
        Paragraph("Cantidades por operación", estilos["Heading2"]),
        _tabla(
            [["Operación", "Código", "Cantidad"]]
            + [[item.get("nombre"), item.get("codigo"), item.get("cantidad", 0)]
               for item in sorted(resumen.get("por_operacion", []), key=lambda x: x.get("codigo", ""))],
            [6.5 * cm, 7.2 * cm, 2.6 * cm],
        ),
        Spacer(1, .25 * cm),
        lollipop_horizontal(
            "Operaciones más frecuentes (máximo diez)",
            [(item.get("nombre") or item.get("codigo") or "Sin nombre", item.get("cantidad"))
             for item in sorted(resumen.get("por_operacion", []),
                                key=lambda fila: (-int(fila.get("cantidad") or 0),
                                                  str(fila.get("codigo", ""))))[:10]],
        ),
        Paragraph(
            "El orden refleja frecuencia registrada, no impacto. El detalle tabular conserva "
            "todas las operaciones incluidas.", estilos["Normal"],
        ),
        PageBreak(),
        Paragraph("Glosario de operaciones", estilos["Heading1"]),
        _tabla(
            [["Nombre humano", "Código técnico", "Significado"]]
            + [[item.get("nombre"), item.get("codigo"), item.get("descripcion")]
               for item in sorted(datos.get("glosario", []), key=lambda x: x.get("codigo", ""))],
            [5.2 * cm, 5.2 * cm, 5.9 * cm],
        ),
        PageBreak(),
        Paragraph("Detalle completo", estilos["Heading1"]),
    ]

    for item in operaciones:
        operacion = item.get("operacion_detalle", {})
        aprobacion = item.get("aprobacion", {})
        historia.extend([
            Paragraph(
                _seguro(f"#{item.get('id')} · {operacion.get('nombre', item.get('operacion'))}"),
                estilos["Heading2"],
            ),
            _tabla([
                ["Momento", "Categoría", "Resultado", "Código técnico"],
                [item.get("momento_local"), operacion.get("categoria"),
                 item.get("resultado") or "No consta", item.get("operacion")],
            ]),
            Paragraph(f"<b>Qué pasó:</b> {_seguro(operacion.get('descripcion'))}", estilos["Normal"]),
            Paragraph(f"<b>Quién:</b> {_seguro(_persona(item.get('actor_detalle')))}", estilos["Normal"]),
            Paragraph(f"<b>Sujeto:</b> {_seguro(_persona(item.get('sujeto_detalle')) or 'No aplica')}", estilos["Normal"]),
            Paragraph(f"<b>Motivo:</b> {_seguro(item.get('motivo'))}", estilos["Normal"]),
        ])
        if item.get("diferencias"):
            historia.append(_tabla(
                [["Campo", "Antes", "Después"]]
                + [[cambio.get("etiqueta"), _visible(cambio.get("antes")), _visible(cambio.get("despues"))]
                   for cambio in item["diferencias"]],
                [5.4 * cm, 5.45 * cm, 5.45 * cm],
            ))
        historia.extend([
            Paragraph(
                f"<b>Segunda aprobación:</b> "
                f"{'requerida y aportada' if aprobacion.get('aportada') else 'requerida y no aportada' if aprobacion.get('requerida') else 'no requerida'}"
                + (f" · {_seguro(_persona(aprobacion.get('aprobador')))}" if aprobacion.get("aportada") else ""),
                estilos["Normal"],
            ),
            Paragraph(f"<b>Metadatos:</b> {_seguro(item.get('detalle'))}", estilos["Normal"]),
            Spacer(1, .32 * cm),
        ])

    historia.extend([
        PageBreak(),
        Paragraph("Nota de privacidad", estilos["Heading1"]),
        Paragraph(
            "El informe no contiene textos de conversación, direcciones IP, huellas del navegador, "
            "ubicaciones ni anexos personales. Los nombres, correos y perfiles se enriquecen al leer "
            "desde las fuentes autorizadas y no se duplican dentro del registro inmutable. Los "
            "identificadores estables se conservan como referencia técnica de trazabilidad.",
            estilos["Normal"],
        ),
    ])
    documento.build(historia)
    return memoria.getvalue()
