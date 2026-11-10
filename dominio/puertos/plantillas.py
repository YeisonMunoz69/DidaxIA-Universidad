from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dominio.diagnostico.clasificador import OpcionRazon


SOCRATICA_APOS = "socratica-apos"


SCAFFOLDING_KQ = "scaffolding-kq"

TWO_TIER = "two-tier"

AUTOCONCEPTO = "autoconcepto"

AUTORREGULACION = "autorregulacion"

CLAVES = (SOCRATICA_APOS, SCAFFOLDING_KQ, TWO_TIER, AUTOCONCEPTO, AUTORREGULACION)


@dataclass(frozen=True)
class Plantilla:

    clave: str
    titulo: str
    preguntas: tuple[str, ...] = ()

    diagnostico: str = ""

    @property
    def utilizable(self) -> bool:
        return bool(self.preguntas)

@dataclass(frozen=True)
class ItemDosNiveles:

    nodo: str
    derivar: str = ""
    opciones: tuple[OpcionRazon, ...] = ()

    enunciado: str = ""

    @property
    def utilizable(self) -> bool:
        return bool(self.derivar) and len(self.opciones) >= 2

    @property
    def ofrecible(self) -> bool:
        return (
            self.utilizable
            and bool(self.enunciado)
            and all(o.texto for o in self.opciones)
        )

    def opcion(self, identificador: str) -> OpcionRazon | None:
        clave = identificador.strip().lower()
        return next((o for o in self.opciones if o.identificador == clave), None)

@runtime_checkable
class PuertoPlantillas(Protocol):

    def secuencia_de(self, concepcion: str) -> Plantilla | None:
        ...

    def plantilla(self, clave: str) -> Plantilla | None:
        ...

    def nodo_del_ejercicio(self, expresion: str) -> str | None:
        ...

    def item_de(self, nodo: str) -> ItemDosNiveles | None:
        ...
