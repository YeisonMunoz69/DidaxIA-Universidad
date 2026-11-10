"""
indice.py — El índice de fragmentos, y su doble para pruebas
=============================================================

`ADR-010` adoptó **la extensión vectorial sobre PostgreSQL**, y su condición se
cumplió el 2026-08-06 cuando E01 reprodujo las 25 cifras. `ADR-004` fijó
PostgreSQL como motor. El modelo de representación es
`intfloat/multilingual-e5-base`, que `06-Guia-de-Reutilizacion.md` §3 marca como
lo que **no se toca** de `kb/vector_store.py`, porque es lo que E01 validó.

Este archivo declara el contrato de índice y trae **una implementación en
memoria**. La de PostgreSQL vive aparte.

Por qué hay un doble, y qué no se puede concluir de él
------------------------------------------------------
Las 120 pruebas del proyecto corren hoy sin ningún servicio externo, y eso vale
la pena conservarlo: una prueba que exige levantar una base deja de ejecutarse
en cuanto molesta. La arquitectura hexagonal es justamente lo que permite probar
la **decisión** —la jerarquía de `ADR-002`, el umbral de `ADR-006`— sin el
almacén.

> ⚠️ **`IndiceEnMemoria` no mide calidad de recuperación y no debe usarse para
> afirmar nada sobre ella.** Su similitud es léxica: solapamiento de términos
> normalizado, sin representación densa. Sirve para que la jerarquía y el umbral
> tengan un colaborador determinista y comprobable, no para saber si el sistema
> recupera bien. **Eso lo mide E01**, con el modelo real, y es la prueba de
> regresión que `03-Plan-de-Construccion.md` dejó como tal.

Confundir las dos cosas sería el error que la guía interna de mantenimiento llama
confundir «preparado» con «hecho»: aquí lo preparado es la forma, y lo medido
sigue siendo lo que midió E01.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Protocol, runtime_checkable

from dominio.puertos.corpus import Fragmento

#: Un término es una secuencia de letras o dígitos. Se parte así y no por
#: espacios porque la notación del corpus mezcla puntuación con símbolos.
_TERMINO = re.compile(r"[0-9a-záéíóúüñ]+")


def _terminos(texto: str) -> frozenset[str]:
    """Términos normalizados de un texto, sin acentos y en minúscula.

    Se retiran los acentos porque el corpus los tiene rotos por obra: la
    extracción de `LOP` produce `funci´on` donde `PUR` produce `función`, y eso
    está documentado en `OE3-Implementacion/codigo/contenido/corpus/FORMATO-DEL-CORPUS.md` §6. Un doble que distinguiera
    esas dos formas mediría el defecto de extracción y no el solapamiento.
    """
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return frozenset(_TERMINO.findall(plano))


#: Dimensión de la representación densa. Sale del `hidden_size` que declara el
#: `config.json` de `intfloat/multilingual-e5-base` —el modelo que E01 validó y
#: que la guía de reutilización marca como lo que **no se toca**—, leído de la
#: ficha del modelo el 2026-08-06 y no de memoria.
#:
#: Está aquí y en el esquema de la base, y esa duplicación es a propósito: el
#: adaptador comprueba que lo que va a guardar tenga esta longitud **antes** de
#: mandarlo, para que el error diga «el codificador devolvió 384» en lugar de un
#: fallo de tipo de la base.
DIMENSION = 768


@runtime_checkable
class Codificador(Protocol):
    """Convierte texto en su representación densa.

    Vive detrás de un contrato propio, y no dentro del adaptador de índice, por
    dos motivos que no son de estilo:

    - **El modelo real arrastra media biblioteca de aprendizaje automático.**
      Meterlo en el adaptador obligaría a instalarla para probar una consulta
      SQL, y las pruebas del proyecto corren hoy sin nada de eso.
    - **Codificar y almacenar son decisiones distintas.** `ADR-002` fijó el
      modelo por medición y `ADR-010` el almacén por otras razones; que puedan
      cambiar por separado es lo que la separación conserva.
    """

    def codificar(self, textos: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Una representación por texto, en el mismo orden."""
        ...


@runtime_checkable
class Indice(Protocol):
    """Lo que la recuperación jerárquica necesita de un almacén.

    Deliberadamente estrecho. `ADR-002` decidió una **estrategia**, y la
    estrategia solo necesita poder pedir los más parecidos, opcionalmente
    acotando a un conjunto de nodos. Todo lo demás —cómo se indexa, cómo se
    persiste, cómo se borra en cascada para `RD-22`— es asunto del adaptador y
    no debe asomar aquí.
    """

    def similares(
        self,
        consulta: str,
        k: int,
        nodos: tuple[str, ...] | None = None,
    ) -> tuple[tuple[Fragmento, float], ...]:
        """Los `k` fragmentos más parecidos, con su similitud, de mayor a menor.

        Si `nodos` viene, la búsqueda se acota a los fragmentos cuyo
        `nodo_grafo` esté en él. Es la recuperación filtrada por nodo activo que
        `RF-RAG-09` pide y que `T5` adoptó para que el grafo enrute sin que el
        índice crezca con él.
        """
        ...


class IndiceEnMemoria:
    """Índice de fragmentos con similitud léxica. **Doble de pruebas.**

    Ver el aviso de la cabecera: no mide calidad de recuperación.
    """

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
            # Coseno sobre vectores binarios de términos. Se elige esta y no
            # Jaccard porque no penaliza que el fragmento sea más largo que la
            # consulta, que es siempre el caso en un corpus de libro de texto.
            puntuados.append((f, comunes / ((len(pregunta) * len(terminos)) ** 0.5)))

        # El desempate es por identificador y no por orden de inserción: dos
        # fragmentos con la misma puntuación deben salir siempre en el mismo
        # orden, o una prueba pasaría o fallaría según cómo se cargó el corpus.
        puntuados.sort(key=lambda par: (-par[1], par[0].identificador))
        return tuple(puntuados[:k])
