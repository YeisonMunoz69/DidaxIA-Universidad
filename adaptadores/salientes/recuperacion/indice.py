from __future__ import annotations

import re
import unicodedata
from typing import Protocol, runtime_checkable

from dominio.puertos.corpus import Fragmento


_TERMINO = re.compile(r"[0-9a-záéíóúüñ]+")


def _terminos(texto: str) -> frozenset[str]:
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return frozenset(_TERMINO.findall(plano))

DIMENSION = 768


@runtime_checkable
class Codificador(Protocol):

    def codificar(self, textos: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        ...

@runtime_checkable
class Indice(Protocol):

    def similares(
        self,
        consulta: str,
        k: int,
        nodos: tuple[str, ...] | None = None,
    ) -> tuple[tuple[Fragmento, float], ...]:

        ...

class IndiceEnMemoria:

    def __init__(self, fragmentos: tuple[Fragmento, ...] = ()) -> None:
        self._fragmentos = tuple(fragmentos)
        self._terminos = {f.identificador: _terminos(f.texto) for f in self._fragmentos}

    def __len__(self) -> int:
        return len(self._fragmentos)

    def similares(
        self,
        consulta: str,
        k: int,
        nodos: tuple[str, ...] | None = None,
    ) -> tuple[tuple[Fragmento, float], ...]:
        pregunta = _terminos(consulta)
        if not pregunta:
            return ()

        puntuados: list[tuple[Fragmento, float]] = []
        for f in self._fragmentos:
            if nodos is not None and f.nodo_grafo not in nodos:
                continue
            terminos = self._terminos[f.identificador]
            if not terminos:
                continue
            comunes = len(pregunta & terminos)
            if not comunes:
                continue

            puntuados.append((f, comunes / ((len(pregunta) * len(terminos)) ** 0.5)))

        puntuados.sort(key=lambda par: (-par[1], par[0].identificador))
        return tuple(puntuados[:k])
