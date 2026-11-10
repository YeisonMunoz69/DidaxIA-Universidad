"""Adaptadores del puerto de corpus.

`cargador.py` lee el contenido escrito a mano en `contenido/corpus/fragmentos/`.
El almacén de recuperación es otro asunto y está condicionado en `ADR-010`.
"""

from adaptadores.salientes.corpus.cargador import (
    FragmentoLeido,
    ResultadoDeCarga,
    ResultadoDeLectura,
    cargar,
    claves_de_obra,
    leer_todos,
)

__all__ = [
    "FragmentoLeido",
    "ResultadoDeCarga",
    "ResultadoDeLectura",
    "cargar",
    "claves_de_obra",
    "leer_todos",
]
