from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Autoridad:

    nombre: str
    filas: int
    texto_libre: bool = False
    alcanzable: bool = True
    nota: str = ""

@dataclass(frozen=True, slots=True)
class InventarioPorTitular:

    sujeto_google: str
    autoridades: tuple[Autoridad, ...] = field(default_factory=tuple)

    @property
    def filas_totales(self) -> int:
        return sum(a.filas for a in self.autoridades)

    @property
    def con_texto_libre(self) -> tuple[Autoridad, ...]:
        return tuple(a for a in self.autoridades if a.texto_libre and a.filas)

    @property
    def fuera_de_alcance(self) -> tuple[Autoridad, ...]:
        return tuple(a for a in self.autoridades if not a.alcanzable and a.filas)

    def como_json(self) -> dict:
        return {
            "sujeto_google": self.sujeto_google,
            "filas_totales": self.filas_totales,
            "autoridades": [
                {
                    "nombre": a.nombre,
                    "filas": a.filas,
                    "texto_libre": a.texto_libre,
                    "alcanzable": a.alcanzable,
                    "nota": a.nota,
                }
                for a in self.autoridades
            ],
        }

@runtime_checkable
class PuertoInventarioDeDatos(Protocol):

    def inventariar(self, sujeto_google: str) -> InventarioPorTitular:
        ...
