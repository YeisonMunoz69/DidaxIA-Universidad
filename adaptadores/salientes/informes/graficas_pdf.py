"""Figuras vectoriales, descriptivas y deterministas para informes impresos.

El estilo científico se adapta al motor ReportLab que ya genera los PDF:
etiquetas negras, escala visible, paleta accesible y valores anotados. No se
infieren tendencias, distribuciones ni relaciones que el corte no contiene.
"""

from __future__ import annotations

from math import isfinite

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String, Wedge
from reportlab.lib import colors

AZUL = colors.HexColor("#3366CC")
GRIS = colors.HexColor("#CFD4DB")
TINTA = colors.black
PALETA = tuple(colors.HexColor(c) for c in ("#2563EB", "#0D9488", "#9333EA", "#D97706", "#DB2777", "#475569"))


def es_resultado_publicable(item: dict) -> bool:
    """Misma regla de publicación del tablero: valor finito y estado disponible."""
    valor = item.get("valor")
    return item.get("estado") == "disponible" and type(valor) in (int, float) and isfinite(valor)


def es_indicador_visible(item: dict) -> bool:
    """Incluye cobertura de los tres fenómenos sin fabricar una cifra publicable."""
    return es_resultado_publicable(item) or (
        (item.get("codigo") in {"conductual.ansiedad_matematica",
                              "aprendizaje.concepciones_dos_niveles",
                              "conductual.reiteracion_tras_correccion",
                              "conductual.hibrido_ps_anx", "aprendizaje.preconcepciones_dialogo",
                              "conductual.hibrido_reiteracion"}
         or str(item.get("codigo", "")).startswith("conductual.observable_"))
        and item.get("estado") in {"sin_datos", "muestra_insuficiente", "datos_incompletos"}
    )


def barras_horizontales(titulo: str, pares: list[tuple[str, object]], *, ancho: int = 470) -> Drawing:
    """Una escala común por figura; no compara unidades distintas."""
    valores = []
    for etiqueta, crudo in pares[:10]:
        try:
            numero = float(crudo)
        except (TypeError, ValueError):
            continue
        if isfinite(numero) and numero >= 0:
            valores.append((str(etiqueta), numero))
    alto = max(66, 54 + len(valores) * 22 + (12 if len(pares) > 10 else 0))
    dibujo = Drawing(ancho, alto)
    dibujo.add(String(0, alto - 15, titulo, fontName="Helvetica-Bold", fontSize=9,
                      fillColor=TINTA))
    if not valores:
        dibujo.add(String(0, alto - 37, "Sin datos comparables en este corte",
                          fontName="Helvetica", fontSize=7.5, fillColor=TINTA))
        return dibujo
    maximo = max((numero for _, numero in valores), default=0)
    inicio = 205
    longitud = ancho - inicio - 55
    for indice, (etiqueta, numero) in enumerate(valores):
        y = alto - 40 - indice * 22
        rotulo = etiqueta if len(etiqueta) <= 39 else etiqueta[:36] + "..."
        dibujo.add(String(0, y, rotulo, fontName="Helvetica", fontSize=7.2,
                          fillColor=TINTA))
        dibujo.add(Line(inicio, y + 2, inicio + longitud, y + 2,
                         strokeColor=GRIS, strokeWidth=.5))
        if maximo:
            dibujo.add(Rect(inicio, y - 1, longitud * numero / maximo, 7,
                            fillColor=PALETA[indice % len(PALETA)], strokeColor=None))
        etiqueta_valor = f"{numero:g}"
        dibujo.add(String(ancho - 44, y, etiqueta_valor, fontName="Helvetica-Bold",
                          fontSize=7.2, fillColor=TINTA))
    if len(pares) > 10:
        dibujo.add(String(0, 6, f"Se muestran 10 de {len(pares)} categorías; consulte la tabla completa.",
                          fontName="Helvetica", fontSize=6.8, fillColor=TINTA))
    return dibujo


def mosaico_proporcion(parte: float, total: float, *, ancho: int = 460) -> Drawing:
    """Mosaico de 100 celdas, aproximación visual etiquetada; cifra exacta al lado."""
    if not all(isfinite(v) for v in (parte, total)) or not 0 <= parte <= total or total <= 0:
        raise ValueError("proporción inválida")
    dibujo = Drawing(ancho, 158)
    dibujo.add(String(0, 145, "Proporción observada · mosaico de 100 celdas", fontName="Helvetica-Bold", fontSize=9, fillColor=TINTA))
    completas = int(parte / total * 100 + .5)
    for i in range(100):
        dibujo.add(Rect((i % 10) * 12, 17 + (9 - i // 10) * 12, 9, 9,
                        fillColor=PALETA[1] if i < completas else GRIS, strokeColor=None))
    dibujo.add(String(150, 108, f"{100 * parte / total:.1f} %", fontName="Helvetica-Bold", fontSize=26, fillColor=PALETA[1]))
    dibujo.add(String(150, 84, f"{parte:g} de {total:g} oportunidades", fontName="Helvetica", fontSize=10))
    dibujo.add(String(150, 60, "Cada celda representa un punto porcentual.", fontName="Helvetica", fontSize=8))
    dibujo.add(String(150, 44, "Mosaico redondeado; la cifra conserva el cálculo.", fontName="Helvetica", fontSize=8))
    dibujo.add(String(150, 22, "No representa una meta ni un nivel de logro.", fontName="Helvetica", fontSize=8))
    return dibujo


def anillo_proporcion(parte: float, total: float, *, ancho: int = 460) -> Drawing:
    """Anillo descriptivo: sector observado y resto de un denominador real."""
    if not all(isfinite(v) for v in (parte, total)) or not 0 <= parte <= total or total <= 0:
        raise ValueError("proporción inválida")
    dibujo = Drawing(ancho, 145)
    dibujo.add(String(0, 132, "Proporción observada · anillo", fontName="Helvetica-Bold", fontSize=9, fillColor=TINTA))
    cx, cy, radio = 65, 67, 48
    dibujo.add(Circle(cx, cy, radio, fillColor=GRIS, strokeColor=None))
    if parte == total:
        dibujo.add(Circle(cx, cy, radio, fillColor=PALETA[2], strokeColor=None))
    elif parte:
        dibujo.add(Wedge(cx, cy, radio, 90, 90 + 360 * parte / total,
                         fillColor=PALETA[2], strokeColor=None))
    dibujo.add(Circle(cx, cy, 28, fillColor=colors.white, strokeColor=None))
    dibujo.add(String(142, 89, f"{100 * parte / total:.1f} %", fontName="Helvetica-Bold",
                      fontSize=24, fillColor=PALETA[2]))
    dibujo.add(String(142, 64, f"{parte:g} de {total:g} oportunidades", fontName="Helvetica", fontSize=9, fillColor=TINTA))
    dibujo.add(String(142, 44, f"Resto del denominador: {total - parte:g}", fontName="Helvetica", fontSize=8, fillColor=TINTA))
    dibujo.add(String(142, 24, "La fracción depende de la definición del KPI.", fontName="Helvetica", fontSize=8, fillColor=TINTA))
    return dibujo


def intervalo_cuartiles(detalle: dict, mediana: float, unidad: str, *, ancho: int = 460) -> Drawing | None:
    """P25–P75 reales y mediana; no fabrica bigotes ni intervalos de confianza."""
    valores = [detalle.get("minimo"), detalle.get("p25"), mediana, detalle.get("p75"), detalle.get("maximo")]
    if any(type(v) not in (int, float) or not isfinite(v) for v in valores):
        return None
    minimo, p25, centro, p75, maximo = valores
    if not minimo <= p25 <= centro <= p75 <= maximo:
        return None
    dibujo = Drawing(ancho, 118)
    dibujo.add(String(0, 104, "Distribución observada · intervalo central", fontName="Helvetica-Bold", fontSize=9))
    inferior, superior = min(0, minimo), max(1, maximo)
    def x(valor):
        return 30 + (ancho - 60) * (valor - inferior) / (superior - inferior)
    dibujo.add(Line(30, 55, ancho - 30, 55, strokeColor=GRIS, strokeWidth=2))
    dibujo.add(Line(x(p25), 55, x(p75), 55, strokeColor=PALETA[2], strokeWidth=12))
    dibujo.add(Circle(x(centro), 55, 5, fillColor=PALETA[0], strokeColor=colors.white))
    dibujo.add(String(30, 33, f"{inferior:g}", fontSize=8))
    dibujo.add(String(ancho - 30, 33, f"{superior:g} {unidad}", textAnchor="end", fontSize=8))
    dibujo.add(String(0, 10, f"P25={p25:g}  |  Mediana={centro:g}  |  P75={p75:g}  · No es un intervalo de confianza", fontSize=8))
    return dibujo


def mapa_disponibilidad(indicadores: list[dict], *, ancho: int = 460) -> Drawing:
    """Recuento por dimensión y estado: no mezcla magnitudes de los KPI."""
    estados = [("disponible", "Disponible", PALETA[1]), ("no_instrumentado", "Sin fuente", PALETA[3]),
               ("sin_datos", "Sin datos", GRIS), ("otros", "Otros estados", PALETA[2])]
    dimensiones = sorted({item["dimension"] for item in indicadores})
    alto = 65 + 27 * len(dimensiones)
    dibujo = Drawing(ancho, alto)
    dibujo.add(String(0, alto - 14, "Mapa de disponibilidad · recuento de indicadores", fontName="Helvetica-Bold", fontSize=9))
    for j, (_, nombre, color) in enumerate(estados):
        dibujo.add(Rect(135 + j * 78, alto - 37, 8, 8, fillColor=color, strokeColor=None))
        dibujo.add(String(146 + j * 78, alto - 36, nombre, fontSize=6.7))
    for i, dimension in enumerate(dimensiones):
        y = alto - 62 - i * 27
        dibujo.add(String(0, y + 5, dimension.capitalize(), fontSize=8))
        for j, (estado, _, color) in enumerate(estados):
            filas = [item for item in indicadores if item["dimension"] == dimension]
            n = sum(item.get("estado") == estado if estado != "otros" else item.get("estado") not in {"disponible", "no_instrumentado", "sin_datos"} for item in filas)
            dibujo.add(Rect(135 + j * 78, y, 67, 20, fillColor=color if n else colors.HexColor("#F1F5F9"), strokeColor=None))
            dibujo.add(String(168 + j * 78, y + 6, str(n), textAnchor="middle", fontName="Helvetica-Bold", fontSize=9,
                              fillColor=colors.white if n and estado != "sin_datos" else TINTA))
    return dibujo


def lollipop_horizontal(titulo: str, pares: list[tuple[str, object]], *, ancho: int = 470) -> Drawing:
    """Ranking de frecuencias con escala cero y marcas de valor directas."""
    validos = []
    for etiqueta, crudo in pares[:10]:
        try:
            numero = float(crudo)
        except (TypeError, ValueError):
            continue
        if isfinite(numero) and numero >= 0:
            validos.append((str(etiqueta), numero))
    alto = max(66, 54 + len(validos) * 22 + (12 if len(pares) > 10 else 0))
    dibujo = Drawing(ancho, alto)
    dibujo.add(String(0, alto - 15, titulo, fontName="Helvetica-Bold", fontSize=9,
                      fillColor=TINTA))
    if not validos:
        dibujo.add(String(0, alto - 37, "Sin datos comparables en este corte",
                          fontName="Helvetica", fontSize=7.5, fillColor=TINTA))
        return dibujo
    maximo = max(numero for _, numero in validos)
    inicio, longitud = 205, ancho - 260
    for indice, (etiqueta, numero) in enumerate(validos):
        y = alto - 40 - indice * 22
        dibujo.add(String(0, y, etiqueta[:36] + ("..." if len(etiqueta) > 36 else ""),
                          fontName="Helvetica", fontSize=7.2, fillColor=TINTA))
        dibujo.add(Line(inicio, y + 2, inicio + longitud, y + 2,
                         strokeColor=GRIS, strokeWidth=.5))
        x = inicio + longitud * numero / max(maximo, 1)
        dibujo.add(Line(inicio, y + 2, x, y + 2, strokeColor=AZUL, strokeWidth=1.25))
        dibujo.add(Circle(x, y + 2, 3.2, fillColor=AZUL, strokeColor=None))
        dibujo.add(String(ancho - 44, y, f"{numero:g}", fontName="Helvetica-Bold",
                          fontSize=7.2, fillColor=TINTA))
    if len(pares) > 10:
        dibujo.add(String(0, 6, f"Se muestran 10 de {len(pares)} categorías; consulte la tabla completa.",
                          fontName="Helvetica", fontSize=6.8, fillColor=TINTA))
    return dibujo


def proporcion_observada(titulo: str, parte: float, total: float, *, ancho: int = 470) -> Drawing:
    """Barra apilada 100 % para una fracción genuina, sin meta inventada."""
    if not all(isfinite(numero) for numero in (parte, total)) or not 0 <= parte <= total or total <= 0:
        raise ValueError("la proporción necesita 0 <= parte <= total y total positivo")
    dibujo = Drawing(ancho, 91)
    dibujo.add(String(0, 76, titulo, fontName="Helvetica-Bold", fontSize=9, fillColor=TINTA))
    inicio, longitud, y = 0, ancho - 5, 44
    ancho_parte = longitud * parte / total
    dibujo.add(Rect(inicio, y, longitud, 12, fillColor=GRIS, strokeColor=None))
    if ancho_parte:
        dibujo.add(Rect(inicio, y, ancho_parte, 12, fillColor=AZUL, strokeColor=None))
    dibujo.add(String(0, 28, f"Observado: {parte:g} de {total:g} ({parte / total * 100:.1f} %)",
                      fontName="Helvetica", fontSize=7.5, fillColor=TINTA))
    dibujo.add(String(0, 11, f"Resto del denominador: {total - parte:g}",
                      fontName="Helvetica", fontSize=7.5, fillColor=TINTA))
    return dibujo


def serie_temporal(titulo: str, puntos: list[tuple[str, object]], *, ancho: int = 470) -> Drawing:
    """Serie con huecos explícitos: un dato suprimido jamás se interpola."""
    visibles = []
    for indice, (etiqueta, crudo) in enumerate(puntos):
        try:
            numero = float(crudo) if crudo is not None else None
        except (TypeError, ValueError):
            numero = None
        visibles.append((indice, str(etiqueta), numero if numero is not None
                         and isfinite(numero) and numero >= 0 else None))
    dibujo = Drawing(ancho, 154)
    dibujo.add(String(0, 139, titulo, fontName="Helvetica-Bold", fontSize=9, fillColor=TINTA))
    if not visibles or all(valor is None for _, _, valor in visibles):
        dibujo.add(String(0, 118, "Sin datos publicables en este corte", fontName="Helvetica",
                          fontSize=7.5, fillColor=TINTA))
        return dibujo
    inicio_x, fin_x, base_y, techo_y = 43, ancho - 25, 38, 111
    maximo = max(valor for _, _, valor in visibles if valor is not None)
    dibujo.add(Line(inicio_x, base_y, fin_x, base_y, strokeColor=TINTA, strokeWidth=.6))
    dibujo.add(Line(inicio_x, base_y, inicio_x, techo_y, strokeColor=TINTA, strokeWidth=.6))
    dibujo.add(String(0, base_y - 2, "0", fontName="Helvetica", fontSize=7, fillColor=TINTA))
    dibujo.add(String(0, techo_y - 2, f"{maximo:g}", fontName="Helvetica", fontSize=7,
                      fillColor=TINTA))
    anterior = None
    for indice, etiqueta, valor in visibles:
        x = ((inicio_x + fin_x) / 2 if len(visibles) == 1 else
             inicio_x + (fin_x - inicio_x) * indice / (len(visibles) - 1))
        if valor is not None:
            y = base_y + (techo_y - base_y) * valor / (maximo if maximo > 0 else 1)
            if anterior is not None and anterior[0] == indice - 1:
                dibujo.add(Line(anterior[1], anterior[2], x, y,
                                 strokeColor=AZUL, strokeWidth=1.2))
            dibujo.add(Circle(x, y, 2.3, fillColor=AZUL, strokeColor=None))
            dibujo.add(String(x, y + 5, f"{valor:g}", fontName="Helvetica", fontSize=6.5,
                              textAnchor="middle", fillColor=TINTA))
            anterior = (indice, x, y)
        else:
            anterior = None
        if len(visibles) <= 10 or indice in {0, len(visibles) - 1} or indice % max(1, len(visibles) // 5) == 0:
            dibujo.add(String(x, 20, etiqueta[-10:], fontName="Helvetica", fontSize=6.2,
                              textAnchor="middle", fillColor=TINTA))
    return dibujo


def perfil_proporciones(titulo: str, indicadores: list[dict], *, ancho: int = 470) -> Drawing | None:
    """Escala común 0–100 % con el valor y n de cada KPI realmente publicado.

    La posición facilita leer cada fracción, no establece un orden de calidad
    entre constructos distintos. Las ausencias no se convierten en barras cero.
    """
    filas = [
        item for item in indicadores
        if item.get("estado") == "disponible"
        and item.get("unidad") == "proporcion"
        and type(item.get("valor")) in (int, float)
        and isfinite(item["valor"]) and 0 <= item["valor"] <= 1
    ]
    if not filas:
        return None
    alto = 55 + len(filas) * 28
    dibujo = Drawing(ancho, alto)
    dibujo.add(String(0, alto - 16, titulo, fontName="Helvetica-Bold", fontSize=9, fillColor=TINTA))
    inicio, longitud = 208, ancho - 275
    for indice, item in enumerate(filas):
        y = alto - 41 - indice * 28
        nombre = str(item.get("nombre") or item.get("codigo") or "KPI")
        nombre = nombre[:35] + ("..." if len(nombre) > 35 else "")
        valor = float(item["valor"])
        dibujo.add(String(0, y, nombre, fontName="Helvetica", fontSize=7.3, fillColor=TINTA))
        dibujo.add(Rect(inicio, y - 1, longitud, 8, fillColor=GRIS, strokeColor=None))
        dibujo.add(Rect(inicio, y - 1, longitud * valor, 8,
                        fillColor=PALETA[indice % len(PALETA)], strokeColor=None))
        muestra = item.get("muestra")
        etiqueta = f"{valor * 100:.1f}%"
        if type(muestra) is int:
            etiqueta += f" · n={muestra}"
        dibujo.add(String(ancho - 2, y, etiqueta, textAnchor="end",
                          fontName="Helvetica-Bold", fontSize=7.2, fillColor=TINTA))
    dibujo.add(String(inicio, 8, "0%", fontName="Helvetica", fontSize=7, fillColor=TINTA))
    dibujo.add(String(inicio + longitud, 8, "100%", textAnchor="end",
                      fontName="Helvetica", fontSize=7, fillColor=TINTA))
    return dibujo
