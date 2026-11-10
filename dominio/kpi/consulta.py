"""
consulta.py — Qué se puede pedir, y qué filtro no se puede honrar todavía
==========================================================================

Una petición de indicadores lleva alcance, actor, periodo y filtros. Este
módulo la valida **antes** de tocar la base, y su parte más importante es la
que rechaza.

Por qué un filtro que no se puede honrar se rechaza en vez de ignorarse
-------------------------------------------------------------------------------
Porque ignorarlo amplía el alcance en silencio. Quien pide «cobertura de
recuperación **del concepto derivada**» y recibe la del curso entero lee una
cifra que cree acotada y no lo está — y el encargo lo prohíbe con nombre
propio: *«filtros manipulados no amplían alcance»*. Un filtro desconocido
tampoco se acepta: aceptarlo y no aplicarlo es el mismo error con otra ropa.

El único filtro reconocido que todavía se rechaza es **cohorte**: no existe la
entidad. `clase_matricula.desde` es la fecha de una matrícula, no una cohorte,
y derivar una de ella sería inventar un concepto de producto dentro de una
consulta.

Concepto se aplica sobre la relación histórica explícita de la migración 24;
corpus y modelo, sobre el evento canónico `turno.respondido`. Las ausencias de
instrumentación siguen siendo ausencias y no ceros.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from dominio.kpi.contratos import Alcance, KPIInvalido, Periodo

#: Los filtros que esta entrega aplica de verdad.
FILTROS_APLICABLES: Final[frozenset[str]] = frozenset({
    "clase", "docente", "facultad", "programa", "semestre",
    "concepto", "version_corpus", "version_modelo",
})

#: Los que el catálogo reconoce y todavía no puede honrar, con su motivo. Se
#: rechazan con este texto para que quien los pida sepa qué falta, en vez de
#: recibir una cifra de otro alcance.
FILTROS_NO_INSTRUMENTADOS: Final[dict[str, str]] = {
    "cohorte": (
        "no existe la entidad cohorte; clase_matricula.desde es la fecha de una "
        "matrícula y derivar de ella una cohorte sería inventar un concepto de "
        "producto dentro de una consulta"
    ),
}


class FiltroNoInstrumentado(KPIInvalido):
    """Se pidió un filtro real del catálogo que todavía no se puede aplicar."""


class FiltroDesconocido(KPIInvalido):
    """Se pidió un filtro que no existe. No se ignora: se dice."""


def _normalizar_filtros(filtros: dict) -> dict[str, str]:
    """Valida forma y dominio antes de que un adaptador componga SQL."""
    normalizados: dict[str, str] = {}
    for nombre, valor_crudo in filtros.items():
        if nombre in FILTROS_NO_INSTRUMENTADOS:
            raise FiltroNoInstrumentado(
                f"el filtro «{nombre}» todavía no se puede aplicar: "
                f"{FILTROS_NO_INSTRUMENTADOS[nombre]}"
            )
        if nombre not in FILTROS_APLICABLES:
            raise FiltroDesconocido(f"«{nombre}» no es un filtro del catálogo")
        if not isinstance(valor_crudo, str) or not valor_crudo.strip():
            raise KPIInvalido(f"el filtro «{nombre}» no tiene un valor utilizable")
        valor = valor_crudo.strip()
        if len(valor) > 160:
            raise KPIInvalido(f"el filtro «{nombre}» excede 160 caracteres")
        if nombre == "semestre":
            valor = _normalizar_semestre(valor)
        normalizados[nombre] = valor
    return normalizados


def _normalizar_semestre(valor: str) -> str:
    try:
        semestre = int(valor)
    except ValueError:
        raise KPIInvalido("el semestre tiene que ser un entero entre 1 y 20") from None
    if not 1 <= semestre <= 20:
        raise KPIInvalido("el semestre tiene que estar entre 1 y 20")
    return str(semestre)


def _validar_codigos(codigos: tuple[str, ...], alcance: Alcance) -> None:
    # Importación local para que el catálogo pueda construir sus definiciones
    # antes de que una consulta intente validarlas.
    from dominio.kpi import catalogo  # noqa: PLC0415

    for codigo in codigos:
        definicion = catalogo.buscar(codigo)
        if definicion is None:
            raise KPIInvalido(f"«{codigo}» no pertenece al catálogo KPI")
        if not definicion.admite(alcance):
            raise KPIInvalido(
                f"«{codigo}» no está disponible para el alcance «{alcance.value}»"
            )


@dataclass(frozen=True, slots=True)
class ConsultaKPI:
    """Lo que se pide, ya validado.

    `clase` es obligatoria en alcance docente y opcional en el institucional.
    No es una comodidad: un docente sin clase pediría el agregado de todas las
    suyas a la vez, y eso todavía no está definido —qué población, qué
    denominador— así que se exige elegir una en vez de inventar la unión.
    """

    alcance: Alcance
    actor: str
    periodo: Periodo
    clase: str | None = None
    filtros: dict = field(default_factory=dict)
    #: Subconjunto de códigos a calcular. Vacío significa «los del alcance».
    codigos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (self.actor or "").strip():
            raise KPIInvalido("una consulta de indicadores necesita un actor")
        if self.alcance is Alcance.DOCENTE and not self.clase:
            raise KPIInvalido("el alcance docente exige elegir una clase")
        object.__setattr__(self, "filtros", _normalizar_filtros(self.filtros))
        # También se impone en el dominio: un llamador que no pase por HTTP no
        # puede pedir códigos ajenos al alcance y recibir una lista recortada.
        _validar_codigos(self.codigos, self.alcance)

    @property
    def filtros_declarados(self) -> dict:
        """Los filtros tal como se aplicaron, para viajar dentro del resultado.

        Incluye siempre el alcance y la clase: sin ellos, dos resultados con
        los mismos filtros pero distinto alcance serían indistinguibles al
        leerlos, que es exactamente cómo se compara lo que no es comparable.
        """
        declarados = {"alcance": self.alcance.value, **self.filtros}
        if self.clase:
            declarados["clase"] = self.clase
        return declarados
