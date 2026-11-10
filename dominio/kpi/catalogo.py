"""
catalogo.py — El catálogo KPI v1.3 completo, ensamblado y consultable
======================================================================

Un catálogo versionado, no una colección de consultas sueltas. Es la diferencia
que el encargo de la Fase 8 marca en su primera línea: *«No empieces dibujando
tarjetas con cifras ficticias. Primero define los contratos y la
trazabilidad»*.

Qué garantiza este módulo
-----------------------------------
- **Códigos únicos y estables.** `_indexar()` falla al importar si dos entradas
  comparten código. Un código es una promesa hacia un informe guardado y hacia
  una comparación longitudinal: repetirlo o cambiarlo rompe las dos.
- **Un orden fijo.** El catálogo es una tupla en el orden de las seis
  dimensiones del encargo, y ese orden es el que ve el consumidor. Un
  diccionario habría dejado que el orden dependiera del intérprete.
- **Ningún KPI sin dimensión ni sin fuentes cuando se declara calculable.** Lo
  impone `DefinicionKPI.__post_init__`, así que un error de catálogo revienta
  al importar y no al servir la primera petición.

Cómo se consulta
-------------------------
`buscar()` para uno, `de_dimension()` para agrupar, `para_alcance()` para
filtrar por rol. No hay una función que devuelva «los calculables»: quién
decide qué se calcula es el adaptador, y una lista aquí se habría quedado vieja
en cuanto se instrumentara el primero.


"""

from __future__ import annotations

from dataclasses import replace

from dominio.kpi.contratos import (
    VERSION_CATALOGO,
    Alcance,
    DefinicionKPI,
    Dimension,
    Instrumento,
    KPIInvalido,
    Unidad,
)
from dominio.kpi.dimensiones import (
    adopcion,
    aprendizaje,
    conductual,
    hibridos,
    institucion,
    observables,
    recuperacion,
    supervision,
)
from dominio.kpi.instrumentos import PROPUESTAS, VERSION

#: El catálogo entero, en el orden de las seis dimensiones del encargo.
CATALOGO: tuple[DefinicionKPI, ...] = (
    *adopcion.CATALOGO,
    *aprendizaje.CATALOGO,
    *recuperacion.CATALOGO,
    *supervision.CATALOGO,
    *conductual.CATALOGO,
    *observables.CATALOGO,
    *hibridos.CATALOGO,
    *institucion.CATALOGO,
)


def _con_instrumento_preliminar(definicion: DefinicionKPI) -> DefinicionKPI:
    if definicion.codigo == "conductual.ansiedad_matematica" and definicion.calculable:
        # El autoinforme propuesto sigue documentado, pero no sustituye la
        # frecuencia léxica que esta versión calcula de verdad.
        return definicion
    propuesta = PROPUESTAS.get(definicion.codigo)
    if propuesta is None:
        return definicion
    familia = propuesta["familia"]
    return replace(
        definicion,
        definicion_operacional=propuesta["pregunta"] + " " + propuesta["criterio"],
        unidad=Unidad.PUNTUACION if familia in ("ordinal", "pareado") else Unidad.PROPORCION,
        numerador=propuesta.get("numerador", propuesta["criterio"]),
        denominador=propuesta.get("denominador", "unidades con observación completa según el instrumento; faltantes excluidos y contabilizados"),
        falta="" if definicion.calculable else propuesta["recoleccion"],
        instrumento=Instrumento(
            nombre="Instrumento-Prototipo · " + definicion.nombre, version=VERSION,
            constructo=propuesta["pregunta"], items=tuple(propuesta["items"]),
            escala="0 a 100 puntos" if familia == "ordinal" else "−100 a 100 puntos" if familia == "pareado" else "0 a 1",
            regla_de_puntuacion=propuesta["formula"],
            minimo_de_observaciones=definicion.muestra_minima,
            falta="" if definicion.calculable else propuesta["recoleccion"],
        ),
    )


CATALOGO = tuple(_con_instrumento_preliminar(d) for d in CATALOGO)


def _indexar(entradas: tuple[DefinicionKPI, ...]) -> dict[str, DefinicionKPI]:
    """El índice por código, comprobando la unicidad al importar.

    Un `dict` por comprensión habría dejado que la segunda entrada pisara a la
    primera en silencio, y las dos habrían seguido apareciendo en la lista: el
    catálogo mostraría cuarenta y `buscar()` devolvería treinta y nueve.
    """
    indice: dict[str, DefinicionKPI] = {}
    for definicion in entradas:
        if definicion.codigo in indice:
            raise KPIInvalido(f"código repetido en el catálogo: «{definicion.codigo}»")
        indice[definicion.codigo] = definicion
    return indice


_POR_CODIGO = _indexar(CATALOGO)


def codigos() -> tuple[str, ...]:
    """Los códigos del catálogo, en su orden."""
    return tuple(definicion.codigo for definicion in CATALOGO)


def buscar(codigo: str) -> DefinicionKPI | None:
    """La definición de ese código, o `None`.

    Devuelve `None` y no levanta porque el llamador natural es una ruta HTTP
    que tiene que contestar 404 con su propio mensaje, y una excepción la
    habría obligado a envolver cada llamada.
    """
    return _POR_CODIGO.get(codigo)


def de_dimension(dimension: Dimension) -> tuple[DefinicionKPI, ...]:
    """Las definiciones de una dimensión, en el orden del catálogo."""
    return tuple(d for d in CATALOGO if d.dimension is dimension)


def para_alcance(alcance: Alcance) -> tuple[DefinicionKPI, ...]:
    """Las definiciones que ese alcance puede pedir.

    Es la primera de las dos barreras de autorización, y la más barata: un
    docente no llega siquiera a nombrar un indicador institucional. La segunda
    —que sólo vea sus clases— la impone el adaptador dentro de la transacción,
    porque una lista de códigos no sabe de quién es una clase.
    """
    return tuple(d for d in CATALOGO if d.admite(alcance))


def como_json(alcance: Alcance | None = None) -> dict:
    """El catálogo publicable, entero o acotado a un alcance."""
    entradas = CATALOGO if alcance is None else para_alcance(alcance)
    return {
        "version_catalogo": VERSION_CATALOGO,
        "alcance": alcance.value if alcance else "completo",
        "dimensiones": [dimension.value for dimension in Dimension],
        "indicadores": [definicion.como_json() for definicion in entradas],
    }
