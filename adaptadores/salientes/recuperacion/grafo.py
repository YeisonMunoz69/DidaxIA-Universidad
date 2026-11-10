from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


TIPOS_DE_ARISTA = (
    "prerrequisito_de",
    "misconception_asociada",
    "se_confunde_con",
    "caso_especial_de",
    "representacion_alternativa_de",
)


MISCONCEPCION = "misconception_asociada"


CATEGORIA_MISCONCEPCION = "Misconception"


@dataclass(frozen=True)
class Nodo:

    identificador: str
    etiqueta: str
    categoria: str = ""
    apos: str = ""
    descripcion: str = ""
    indicador_observable: str = ""

    sinonimos: tuple[str, ...] = ()

    formas_de_consulta: tuple[str, ...] | None = None

class GrafoEnMemoria:

    def __init__(self, definicion: dict) -> None:
        self._nodos: dict[str, Nodo] = {}
        self._salientes: dict[str, list[tuple[str, str]]] = {}

        for n in definicion.get("nodes", []):
            self._nodos[n["id"]] = Nodo(
                identificador=n["id"],
                etiqueta=n.get("label", ""),
                categoria=n.get("categoria", ""),
                apos=n.get("apos", ""),
                descripcion=n.get("descripcion", ""),
                indicador_observable=n.get("indicador_observable", ""),
                sinonimos=tuple(n.get("sinonimos", ())),
                formas_de_consulta=(
                    tuple(n["formas_de_consulta"])
                    if "formas_de_consulta" in n
                    else None
                ),
            )

        for e in definicion.get("edges", []):
            self._salientes.setdefault(e["source"], []).append((e["target"], e["type"]))

    @classmethod
    def desde_archivo(cls, ruta: Path) -> GrafoEnMemoria:
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def validar(self) -> list[str]:
        fallos = []

        for identificador in self.conceptos():
            nodo = self._nodos[identificador]
            if nodo.sinonimos and nodo.formas_de_consulta is None:
                fallos.append(
                    f"{identificador}: declara «sinonimos» y no «formas_de_consulta»"
                    " — el reparto de D-25 quedó a medias"
                )
        for origen, destinos in self._salientes.items():
            if origen not in self._nodos:
                fallos.append(f"arista desde un nodo inexistente «{origen}»")
            for destino, tipo in destinos:
                if tipo not in TIPOS_DE_ARISTA:
                    fallos.append(f"{origen}→{destino}: tipo de arista desconocido «{tipo}»")

                if tipo != MISCONCEPCION and destino not in self._nodos:
                    fallos.append(f"{origen}→{destino}: destino inexistente")
        return fallos

    def __len__(self) -> int:
        return len(self._nodos)

    @property
    def total_aristas(self) -> int:
        return sum(len(v) for v in self._salientes.values())

    def identificadores(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodos))

    def conceptos(self) -> tuple[str, ...]:
        return tuple(
            i for i in self.identificadores()
            if self._nodos[i].categoria != CATEGORIA_MISCONCEPCION
        )

    def nodo(self, identificador: str) -> Nodo | None:
        return self._nodos.get(identificador)

    def vecinos(self, identificador: str, tipo: str | None = None) -> tuple[str, ...]:
        if identificador not in self._nodos:
            return ()
        vistos: list[str] = []
        for destino, t in self._salientes.get(identificador, []):
            if tipo is not None and t != tipo:
                continue
            if destino not in vistos:
                vistos.append(destino)
        return tuple(vistos)

    def concepciones_de(self, identificador: str) -> tuple[str, ...]:
        return self.vecinos(identificador, tipo=MISCONCEPCION)
