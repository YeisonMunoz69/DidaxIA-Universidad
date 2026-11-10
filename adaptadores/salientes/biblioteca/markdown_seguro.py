"""
markdown_seguro.py — Markdown del corpus convertido a bloques tipados
=======================================================================

La Fase 5 exige *«render Markdown seguro mediante una tubería confiable»* y
enumera lo que hay que bloquear: scripts, manejadores de eventos, HTML
inesperado, `javascript:`, `data:` no autorizado, URL peligrosas, incrustaciones
arbitrarias y rutas internas.

**Este módulo no sanea HTML: no produce HTML.**
--------------------------------------------------
Sanear es quitarle a una cadena lo que puede hacer daño, y siempre queda la
duda de si se quitó todo. Aquí el Markdown se convierte en una lista de bloques
y trozos con tipo —párrafo, lista, tabla, matemática, texto, énfasis— y la
interfaz los pinta con nodos de texto. Nunca hay una cadena de HTML que alguien
pueda insertar con `innerHTML`, así que **no existe la categoría de ataque**:
un `<script>` escrito en un fragmento llega al navegador como los catorce
caracteres que es, y se ven.

La única vía que sí necesita lista blanca son los enlaces, porque un enlace sí
lleva un destino ejecutable. Se admiten `http` y `https` y nada más; todo lo
demás se degrada a texto y **se cuenta**, para que un fragmento con un enlace
raro no pase inadvertido.

La matemática se extrae ANTES que el énfasis, y no es un detalle
-----------------------------------------------------------------
`$x_1$ y $x_2$` lleva dos guiones bajos. Un analizador que busque énfasis
primero los toma por una marca de cursiva y devuelve `$x1$ y $x2$` con el texto
intermedio en cursiva: la fórmula queda **cambiada**, no sólo mal pintada. Por
eso `$$…$$` y `$…$` se apartan en el primer paso y el resto se analiza sobre lo
que queda.


"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

#: Tope de tamaño de lo que se convierte. Un fragmento del corpus ronda 1 KB y
#: una parte de obra puede rondar cientos; por encima de esto se corta y se
#: dice. Sin tope, un archivo corrupto de 200 MB bloquea al servidor entero.
LIMITE_DE_CARACTERES = 400_000

#: Tope de líneas, por el mismo motivo y contra el caso contrario: un archivo
#: pequeño con un millón de saltos de línea.
LIMITE_DE_LINEAS = 40_000

#: Esquemas admitidos en un enlace. **Lista blanca.** `javascript:`, `data:`,
#: `vbscript:`, `file:` y cualquier otro caen a texto plano.
ESQUEMAS_ADMITIDOS = ("http://", "https://")

_MATEMATICA_DISPLAY = re.compile(r"^\s*\$\$(.*?)\$\$\s*$", re.S)
#: Matemática en línea. `\$` escapado no abre fórmula: es un signo de moneda.
_MATEMATICA_INLINE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
_FUERTE = re.compile(r"\*\*(.+?)\*\*", re.S)
_ENFASIS = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)
_CODIGO = re.compile(r"`([^`\n]+)`")
_ENLACE = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)\)")
_ELEMENTO_SIN_ORDEN = re.compile(r"^\s*[-*+]\s+(.*)$")
_ELEMENTO_ORDENADO = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_ENCABEZADO = re.compile(r"^(#{1,6})\s+(.*)$")
_REGLA = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_SEPARADOR_DE_TABLA = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


@dataclass(frozen=True)
class Trozo:
    """Un fragmento de línea con su tipo. `destino` sólo lo usa `enlace`."""

    tipo: str
    texto: str
    destino: str = ""


@dataclass
class Bloque:
    """Un bloque del documento. Los campos que no aplican van vacíos."""

    tipo: str
    trozos: list[Trozo] = field(default_factory=list)
    #: `encabezado`
    nivel: int = 0
    #: `lista`
    ordenada: bool = False
    elementos: list[list[Trozo]] = field(default_factory=list)
    #: `matematica`
    latex: str = ""
    #: `tabla`
    encabezados: list[list[Trozo]] = field(default_factory=list)
    filas: list[list[list[Trozo]]] = field(default_factory=list)


@dataclass
class Documento:
    """El resultado de convertir un Markdown, con lo que hubo que degradar."""

    bloques: list[Bloque] = field(default_factory=list)
    #: Enlaces cuyo esquema no está en la lista blanca. Se conservaron como
    #: texto y se cuentan aquí para que el equipo los vea en una auditoría.
    enlaces_rechazados: list[str] = field(default_factory=list)
    #: Si el contenido se cortó por exceder los topes.
    truncado: bool = False

    def como_json(self) -> dict:
        return asdict(self)


def convertir(texto: str) -> Documento:
    """Convierte Markdown en bloques tipados. **Nunca levanta.**

    Un archivo ilegible produce un documento vacío, no una excepción: quien
    llama está sirviendo una pantalla y prefiere un estado «no se pudo leer» a
    un 500.
    """
    documento = Documento()
    if not isinstance(texto, str) or not texto.strip():
        return documento

    if len(texto) > LIMITE_DE_CARACTERES:
        texto = texto[:LIMITE_DE_CARACTERES]
        documento.truncado = True

    lineas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lineas) > LIMITE_DE_LINEAS:
        lineas = lineas[:LIMITE_DE_LINEAS]
        documento.truncado = True

    _convertir_lineas(lineas, documento)
    return documento


def _convertir_lineas(lineas: list[str], documento: Documento) -> None:
    """El bucle principal. La decisión de qué es cada línea vive aparte.

    Se separan porque son dos cosas distintas: aquí se acumula el párrafo
    abierto y se avanza; en `_tomar_bloque` se reconoce la forma. Juntas, la
    función pasaba de la complejidad que `PM-B22` fijó para todo el proyecto.
    """
    indice = 0
    parrafo: list[str] = []

    while indice < len(lineas):
        linea = lineas[indice]
        desnuda = linea.strip()

        if not desnuda:
            _cerrar_parrafo(parrafo, documento)
            indice += 1
            continue

        siguiente = _tomar_bloque(lineas, indice, documento, parrafo)
        if siguiente is not None:
            indice = siguiente
            continue

        parrafo.append(desnuda)
        indice += 1

    _cerrar_parrafo(parrafo, documento)


def _cerrar_parrafo(parrafo: list[str], documento: Documento) -> None:
    """Emite el párrafo acumulado, si hay alguno, y lo vacía."""
    if parrafo:
        documento.bloques.append(
            Bloque(tipo="parrafo", trozos=_trozos(" ".join(parrafo), documento))
        )
        parrafo.clear()


def _tomar_bloque(
    lineas: list[str], indice: int, documento: Documento, parrafo: list[str]
) -> int | None:
    """Reconoce un bloque en `indice` y devuelve dónde sigue, o `None`.

    `None` significa «esto es prosa corriente», y el bucle la acumula. Cada
    rama cierra antes el párrafo abierto: un bloque no puede quedar dentro del
    párrafo que venía antes.
    """
    linea = lineas[indice]
    desnuda = linea.strip()

    if _REGLA.match(linea):
        _cerrar_parrafo(parrafo, documento)
        documento.bloques.append(Bloque(tipo="regla"))
        return indice + 1

    if desnuda.startswith("$$"):
        _cerrar_parrafo(parrafo, documento)
        return _tomar_matematica(lineas, indice, documento)

    encabezado = _ENCABEZADO.match(desnuda)
    if encabezado:
        _cerrar_parrafo(parrafo, documento)
        documento.bloques.append(
            Bloque(
                tipo="encabezado",
                nivel=len(encabezado.group(1)),
                trozos=_trozos(encabezado.group(2), documento),
            )
        )
        return indice + 1

    if desnuda.startswith("|") and _es_tabla(lineas, indice):
        _cerrar_parrafo(parrafo, documento)
        return _tomar_tabla(lineas, indice, documento)

    if desnuda.startswith(">"):
        _cerrar_parrafo(parrafo, documento)
        return _tomar_cita(lineas, indice, documento)

    if _ELEMENTO_SIN_ORDEN.match(linea) or _ELEMENTO_ORDENADO.match(linea):
        _cerrar_parrafo(parrafo, documento)
        return _tomar_lista(lineas, indice, documento)

    return None


def _tomar_matematica(lineas: list[str], indice: int, documento: Documento) -> int:
    """Un bloque `$$…$$`, en una línea o en varias."""
    primera = lineas[indice].strip()
    en_una = _MATEMATICA_DISPLAY.match(primera)
    if en_una:
        documento.bloques.append(Bloque(tipo="matematica", latex=en_una.group(1).strip()))
        return indice + 1

    cuerpo = [primera[2:]]
    siguiente = indice + 1
    while siguiente < len(lineas) and "$$" not in lineas[siguiente]:
        cuerpo.append(lineas[siguiente])
        siguiente += 1
    if siguiente < len(lineas):
        cuerpo.append(lineas[siguiente].split("$$")[0])
        siguiente += 1
    documento.bloques.append(Bloque(tipo="matematica", latex="\n".join(cuerpo).strip()))
    return siguiente


def _es_tabla(lineas: list[str], indice: int) -> bool:
    """Una tabla necesita su fila de separación justo debajo del encabezado."""
    return indice + 1 < len(lineas) and bool(_SEPARADOR_DE_TABLA.match(lineas[indice + 1]))


def _celdas(linea: str) -> list[str]:
    desnuda = linea.strip()
    if desnuda.startswith("|"):
        desnuda = desnuda[1:]
    if desnuda.endswith("|"):
        desnuda = desnuda[:-1]
    return [c.strip() for c in desnuda.split("|")]


def _tomar_tabla(lineas: list[str], indice: int, documento: Documento) -> int:
    bloque = Bloque(tipo="tabla")
    bloque.encabezados = [_trozos(c, documento) for c in _celdas(lineas[indice])]
    siguiente = indice + 2
    while siguiente < len(lineas) and lineas[siguiente].strip().startswith("|"):
        bloque.filas.append([_trozos(c, documento) for c in _celdas(lineas[siguiente])])
        siguiente += 1
    documento.bloques.append(bloque)
    return siguiente


def _tomar_cita(lineas: list[str], indice: int, documento: Documento) -> int:
    """Una cita se aplana a un párrafo marcado.

    **No se anida.** El corpus no usa citas dentro de citas y admitir la
    recursión abriría un camino a agotar la pila con un archivo hecho de `>`.
    """
    cuerpo: list[str] = []
    siguiente = indice
    while siguiente < len(lineas) and lineas[siguiente].strip().startswith(">"):
        cuerpo.append(lineas[siguiente].strip().lstrip(">").strip())
        siguiente += 1
    documento.bloques.append(
        Bloque(tipo="cita", trozos=_trozos(" ".join(c for c in cuerpo if c), documento))
    )
    return siguiente


def _tomar_lista(lineas: list[str], indice: int, documento: Documento) -> int:
    ordenada = bool(_ELEMENTO_ORDENADO.match(lineas[indice]))
    bloque = Bloque(tipo="lista", ordenada=ordenada)
    siguiente = indice
    while siguiente < len(lineas):
        linea = lineas[siguiente]
        coincidencia = (
            _ELEMENTO_ORDENADO.match(linea) if ordenada else _ELEMENTO_SIN_ORDEN.match(linea)
        )
        if coincidencia:
            bloque.elementos.append(_trozos(coincidencia.group(1), documento))
            siguiente += 1
            continue
        # Una línea suelta e indentada continúa el elemento anterior.
        if linea.strip() and linea.startswith((" ", "\t")) and bloque.elementos:
            bloque.elementos[-1].extend(_trozos(" " + linea.strip(), documento))
            siguiente += 1
            continue
        break
    documento.bloques.append(bloque)
    return siguiente


def _trozos(texto: str, documento: Documento) -> list[Trozo]:
    """Divide una línea en trozos tipados. La matemática se aparta primero."""
    if not texto:
        return []

    salida: list[Trozo] = []
    posicion = 0
    for m in _MATEMATICA_INLINE.finditer(texto):
        if m.start() > posicion:
            salida.extend(_trozos_de_texto(texto[posicion : m.start()], documento))
        salida.append(Trozo(tipo="matematica", texto=m.group(1)))
        posicion = m.end()
    if posicion < len(texto):
        salida.extend(_trozos_de_texto(texto[posicion:], documento))
    return salida


def _trozos_de_texto(texto: str, documento: Documento) -> list[Trozo]:
    """Énfasis, código y enlaces sobre un tramo que ya no lleva matemática."""
    if not texto:
        return []

    for expresion, tipo in ((_CODIGO, "codigo"), (_FUERTE, "fuerte"), (_ENFASIS, "enfasis")):
        m = expresion.search(texto)
        if m:
            return [
                *_trozos_de_texto(texto[: m.start()], documento),
                Trozo(tipo=tipo, texto=m.group(1)),
                *_trozos_de_texto(texto[m.end() :], documento),
            ]

    m = _ENLACE.search(texto)
    if m:
        rotulo, destino = m.group(1), m.group(2)
        if destino.lower().startswith(ESQUEMAS_ADMITIDOS):
            trozo = Trozo(tipo="enlace", texto=rotulo or destino, destino=destino)
        else:
            # Esquema no admitido, ruta relativa o ruta interna del servidor.
            # Se degrada a texto: el estudiante ve lo que decía y no puede
            # pulsarlo, que es lo contrario de esconder el problema.
            documento.enlaces_rechazados.append(destino)
            trozo = Trozo(tipo="texto", texto=f"{rotulo} ({destino})" if rotulo else destino)
        return [
            *_trozos_de_texto(texto[: m.start()], documento),
            trozo,
            *_trozos_de_texto(texto[m.end() :], documento),
        ]

    return [Trozo(tipo="texto", texto=texto)]
