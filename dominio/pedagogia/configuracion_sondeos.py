"""Estado curricular compartido entre el panel investigador y la oferta digital."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

NODOS_DIGITALES = frozenset({"N08", "N14", "N05"})
NODOS_CONFIGURABLES = frozenset({"L-01", *NODOS_DIGITALES})


@dataclass(frozen=True, slots=True)
class ConfiguracionSondeos:
    l01_aula: bool = True
    n08_digital: bool = False
    n14_digital: bool = False
    n05_digital: bool = False
    umbral_intentos: int = 2
    actualizado_en: str | None = None

    def habilitado(self, nodo: str) -> bool:
        return {
            "L-01": self.l01_aula,
            "N08": self.n08_digital,
            "N14": self.n14_digital,
            "N05": self.n05_digital,
        }.get(nodo, False)

    def como_json(self) -> dict:
        return {
            "nodos": {
                "L-01": {"habilitado": self.l01_aula, "canal": "papel"},
                "N08": {"habilitado": self.n08_digital, "canal": "digital"},
                "N14": {"habilitado": self.n14_digital, "canal": "digital"},
                "N05": {"habilitado": self.n05_digital, "canal": "digital"},
            },
            "umbral_intentos": self.umbral_intentos,
            "actualizado_en": self.actualizado_en,
        }


class PuertoConfiguracionSondeos(Protocol):
    def consultar(self) -> ConfiguracionSondeos: ...
    def cambiar_nodo(self, nodo: str, habilitado: bool, actor: str) -> ConfiguracionSondeos: ...
    def cambiar_umbral(self, umbral: int, actor: str) -> ConfiguracionSondeos: ...
