from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


LIMITE_DE_CARACTERES = 400_000


LIMITE_DE_LINEAS = 40_000


ESQUEMAS_ADMITIDOS = ("http://", "https://")

_MATEMATICA_DISPLAY = re.compile(r"^\s*\$\$(.*?)\$\$\s*$", re.S)

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

    tipo: str
    texto: str
    destino: str = ""

@dataclass
class Bloque:

    tipo: str
    trozos: list[Trozo] = field(default_factory=list)

    nivel: int = 0

    ordenada: bool = False
    elementos: list[list[Trozo]] = field(default_factory=list)

    latex: str = ""

    encabezados: list[list[Trozo]] = field(default_factory=list)
    filas: list[list[list[Trozo]]] = field(default_factory=list)

@dataclass
class Documento:

    bloques: list[Bloque] = field(default_factory=list)

    enlaces_rechazados: list[str] = field(default_factory=list)

    truncado: bool = False

    def como_json(self) -> dict:
        return asdict(self)

def convertir(texto: str) -> Documento:
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
    if parrafo:
        documento.bloques.append(
            Bloque(tipo="parrafo", trozos=_trozos(" ".join(parrafo), documento))
        )
        parrafo.clear()

def _tomar_bloque(
    lineas: list[str], indice: int, documento: Documento, parrafo: list[str]
) -> int | None:

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

        if linea.strip() and linea.startswith((" ", "\t")) and bloque.elementos:
            bloque.elementos[-1].extend(_trozos(" " + linea.strip(), documento))
            siguiente += 1
            continue
        break
    documento.bloques.append(bloque)
    return siguiente

def _trozos(texto: str, documento: Documento) -> list[Trozo]:
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

            documento.enlaces_rechazados.append(destino)
            trozo = Trozo(tipo="texto", texto=f"{rotulo} ({destino})" if rotulo else destino)
        return [
            *_trozos_de_texto(texto[: m.start()], documento),
            trozo,
            *_trozos_de_texto(texto[m.end() :], documento),
        ]

    return [Trozo(tipo="texto", texto=texto)]
