from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from dominio.kpi.contratos import Alcance, KPIInvalido, Periodo


FILTROS_APLICABLES: Final[frozenset[str]] = frozenset({
    "clase", "docente", "facultad", "programa", "semestre",
    "concepto", "version_corpus", "version_modelo",
})


FILTROS_NO_INSTRUMENTADOS: Final[dict[str, str]] = {
    "cohorte": (
        "no existe la entidad cohorte; clase_matricula.desde es la fecha de una "
        "matrícula y derivar de ella una cohorte sería inventar un concepto de "
        "producto dentro de una consulta"
    ),
}


class FiltroNoInstrumentado(KPIInvalido):
    pass

class FiltroDesconocido(KPIInvalido):
    pass

def _normalizar_filtros(filtros: dict) -> dict[str, str]:
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
    from dominio.kpi import catalogo

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

    alcance: Alcance
    actor: str
    periodo: Periodo
    clase: str | None = None
    filtros: dict = field(default_factory=dict)

    codigos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (self.actor or "").strip():
            raise KPIInvalido("una consulta de indicadores necesita un actor")
        if self.alcance is Alcance.DOCENTE and not self.clase:
            raise KPIInvalido("el alcance docente exige elegir una clase")
        object.__setattr__(self, "filtros", _normalizar_filtros(self.filtros))

        _validar_codigos(self.codigos, self.alcance)

    @property
    def filtros_declarados(self) -> dict:
        declarados = {"alcance": self.alcance.value, **self.filtros}
        if self.clase:
            declarados["clase"] = self.clase
        return declarados
