from dataclasses import dataclass
from typing import Protocol

from dominio.modelo.factores_conductuales import ObservacionConductual


@dataclass(frozen=True)
class LecturaSemantica:
    clase: str
    evidencia: str
    motivo: str
    estrategia_solicitada: str = ""
    pide_menos_preguntas: bool = False
    propone_solucion: bool = False
    modelo: str = ""
    necesidad: str = ""
    factores: tuple[ObservacionConductual, ...] = ()
    error_factores: str = ""
    actos: tuple[dict, ...] = ()

class PuertoInterpretacion(Protocol):
    def interpretar(self, entrada: dict) -> LecturaSemantica:
        ...
