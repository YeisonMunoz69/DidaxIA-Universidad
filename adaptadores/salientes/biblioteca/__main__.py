from __future__ import annotations

import sys
from pathlib import Path

from adaptadores.salientes.biblioteca.inventario import auditar, como_texto


def _raiz_del_corpus() -> Path:
    return Path(__file__).resolve().parents[3] / "contenido" / "corpus"

def principal(argumentos: list[str]) -> int:
    raiz = _raiz_del_corpus()
    inventario = auditar(raiz)
    print(inventario.como_json() if "--json" in argumentos else como_texto(inventario))
    return 0

if __name__ == "__main__":
    raise SystemExit(principal(sys.argv[1:]))
