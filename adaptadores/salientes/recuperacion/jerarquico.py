from __future__ import annotations

import collections
import math
import re
import unicodedata
from collections.abc import Iterable

from adaptadores.salientes.recuperacion.grafo import GrafoEnMemoria
from adaptadores.salientes.recuperacion.indice import Indice
from dominio.puertos.corpus import Fragmento, Recuperacion


K_ADOPTADO = 3


UMBRAL_INICIAL = 0.70

_TERMINO = re.compile(r"[0-9a-záéíóúüñ]+")


_VACIAS = frozenset(
    (
        "de", "la", "el", "los", "las", "un", "una", "y", "o", "en", "para",
        "por", "con", "que", "como", "se", "su", "sus", "del", "al", "es",
        "son", "este", "esta", "esto", "cual", "cuales", "cuando", "donde",
    )
)


def _palabras(texto: str) -> list[str]:
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return [p for p in _TERMINO.findall(plano) if p not in _VACIAS]

def _terminos(texto: str) -> frozenset[str]:
    return frozenset(_palabras(texto))

MARGEN_INICIAL = 2.0


class PerfilLexico:

    def __init__(self, pesos: dict[str, dict[str, float]]) -> None:
        self._pesos = pesos

    @classmethod
    def desde_fragmentos(cls, fragmentos: Iterable[Fragmento]) -> PerfilLexico:
        cuentas: dict[str, collections.Counter] = {}
        for f in fragmentos:
            if f.nodo_grafo:
                cuentas.setdefault(f.nodo_grafo, collections.Counter()).update(
                    _palabras(f.texto)
                )
        if not cuentas:
            return cls({})

        total_nodos = len(cuentas)
        aparece: collections.Counter = collections.Counter()
        for c in cuentas.values():
            aparece.update(c.keys())

        pesos = {}
        for identificador, c in cuentas.items():
            largo = sum(c.values())

            pesos[identificador] = {
                t: (v / largo) * math.log(total_nodos / aparece[t])
                for t, v in c.items()
                if aparece[t] < total_nodos
            }
        return cls(pesos)

    def __len__(self) -> int:
        return len(self._pesos)

    def nodos(self) -> tuple[str, ...]:
        return tuple(sorted(self._pesos))

    def candidato(self, pregunta: frozenset[str], margen: float) -> str | None:
        puntos = sorted(
            (
                (sum(pesos.get(t, 0.0) for t in pregunta), identificador)
                for identificador, pesos in self._pesos.items()
            ),
            key=lambda par: (-par[0], par[1]),
        )
        if not puntos or puntos[0][0] <= 0.0:
            return None
        if len(puntos) > 1 and puntos[0][0] < margen * puntos[1][0]:
            return None
        return puntos[0][1]

class RecuperadorJerarquico:

    def __init__(
        self,
        indice: Indice,
        grafo: GrafoEnMemoria,
        umbral: float = UMBRAL_INICIAL,
        perfil: PerfilLexico | None = None,
        margen: float = MARGEN_INICIAL,
        prerrequisitos: bool = True,
    ) -> None:
        self._indice = indice
        self._grafo = grafo
        self._umbral = umbral

        self._perfil = perfil
        self._margen = margen

        self._prerrequisitos = prerrequisitos

        self._formas: dict[str, tuple[frozenset[str], ...]] = {}
        for identificador in grafo.conceptos():
            n = grafo.nodo(identificador)
            if n is None:
                continue

            formas = [_terminos(n.etiqueta)]
            formas += [_terminos(s) for s in (n.formas_de_consulta or ())]
            self._formas[identificador] = tuple(f for f in formas if f)

        self._especializaciones: dict[str, frozenset[str]] = {
            i: self._descendientes(grafo, i) for i in self._formas
        }

        reparto: dict[str, int] = {}
        for formas in self._formas.values():
            for termino in {t for f in formas for t in f}:
                reparto[termino] = reparto.get(termino, 0) + 1
        self._peso_de_termino: dict[str, float] = {
            t: 1.0 / n for t, n in reparto.items()
        }

    @staticmethod
    def _descendientes(grafo: GrafoEnMemoria, raiz: str) -> frozenset[str]:
        vistos: set[str] = set()
        pila = [raiz]
        while pila:
            for sucesor in grafo.vecinos(pila.pop(), tipo="prerrequisito_de"):
                if sucesor not in vistos:
                    vistos.add(sucesor)
                    pila.append(sucesor)
        return frozenset(vistos)

    def identificar_nodo(self, consulta: str) -> str | None:
        pregunta = _terminos(consulta)
        if not pregunta:
            return None
        nombrado = self._por_forma_nombrada(pregunta)
        if nombrado is not None:
            return nombrado
        if self._perfil is None:
            return None
        return self._perfil.candidato(pregunta, self._margen)

    def _peso_de_forma(self, forma: frozenset[str]) -> float:
        return sum(self._peso_de_termino.get(t, 1.0) for t in forma)

    def _por_forma_nombrada(self, pregunta: frozenset[str]) -> str | None:
        mejor: dict[str, float] = {}
        for identificador, formas in self._formas.items():
            for forma in formas:

                if forma <= pregunta:
                    peso = self._peso_de_forma(forma)
                    if peso > mejor.get(identificador, 0.0):
                        mejor[identificador] = peso
        if not mejor:
            return None

        cima = max(mejor.values())
        empatados = [i for i, p in mejor.items() if round(p, 6) == round(cima, 6)]
        if len(empatados) == 1:
            return empatados[0]
        return self._desempatar(empatados)

    def _desempatar(self, empatados: list[str]) -> str:
        for i in empatados:
            if all(i in self._especializaciones[j] for j in empatados if j != i):
                return i
        orden = list(self._formas)
        return min(empatados, key=orden.index)

    def recuperar(
        self,
        consulta: str,
        nodo: str | None = None,
        k: int = K_ADOPTADO,
    ) -> Recuperacion:

        entrada = nodo or self.identificar_nodo(consulta)

        if entrada is not None and self._grafo.nodo(entrada) is not None:

            alcance = (entrada,)
            if self._prerrequisitos:
                alcance += self._grafo.vecinos(entrada, tipo="prerrequisito_de")
            candidatos = self._indice.similares(consulta, k=k, nodos=alcance)

            if not candidatos:
                candidatos = self._indice.similares(consulta, k=k)
        else:

            candidatos = self._indice.similares(consulta, k=k)

        admitidos = tuple((f, s) for f, s in candidatos if s >= self._umbral)

        if not admitidos:

            return Recuperacion(fragmentos=(), similitudes=(), sin_fuente=True)

        return Recuperacion(
            fragmentos=tuple(f for f, _ in admitidos),
            similitudes=tuple(s for _, s in admitidos),
            sin_fuente=False,
        )
