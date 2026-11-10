"""Adaptadores de la biblioteca de fuentes · Fase 5.

`catalogo.py` implementa `PuertoBiblioteca` leyendo `FUENTES.md`, `PARTES.md` y
`contenido/corpus/fragmentos/`. `inventario.py` audita esos mismos archivos sin
escribir nada, y es la herramienta reproducible que la fase exige.
"""

from adaptadores.salientes.biblioteca.catalogo import (
    CatalogoDeFuentes,
    FichaDeFragmento,
    InformeDelCatalogo,
)

__all__ = ["CatalogoDeFuentes", "FichaDeFragmento", "InformeDelCatalogo"]
