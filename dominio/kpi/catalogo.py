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
    indice: dict[str, DefinicionKPI] = {}
    for definicion in entradas:
        if definicion.codigo in indice:
            raise KPIInvalido(f"código repetido en el catálogo: «{definicion.codigo}»")
        indice[definicion.codigo] = definicion
    return indice

_POR_CODIGO = _indexar(CATALOGO)


def codigos() -> tuple[str, ...]:
    return tuple(definicion.codigo for definicion in CATALOGO)

def buscar(codigo: str) -> DefinicionKPI | None:
    return _POR_CODIGO.get(codigo)

def de_dimension(dimension: Dimension) -> tuple[DefinicionKPI, ...]:
    return tuple(d for d in CATALOGO if d.dimension is dimension)

def para_alcance(alcance: Alcance) -> tuple[DefinicionKPI, ...]:
    return tuple(d for d in CATALOGO if d.admite(alcance))

def como_json(alcance: Alcance | None = None) -> dict:
    entradas = CATALOGO if alcance is None else para_alcance(alcance)
    return {
        "version_catalogo": VERSION_CATALOGO,
        "alcance": alcance.value if alcance else "completo",
        "dimensiones": [dimension.value for dimension in Dimension],
        "indicadores": [definicion.como_json() for definicion in entradas],
    }
