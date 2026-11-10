"""
__main__.py — La auditoría del corpus, desde la línea de órdenes
==================================================================

    C:\\Python313\\python.exe -m adaptadores.salientes.biblioteca
    C:\\Python313\\python.exe -m adaptadores.salientes.biblioteca --json
    C:\\Python313\\python.exe -m adaptadores.salientes.biblioteca --partes

**No escribe ningún archivo.** `--partes` propone filas para `PARTES.md` y las
imprime; pegarlas es una decisión humana y queda en un commit con nombre.

El código de salida es 0 siempre que la auditoría se pueda ejecutar. Un corpus
con huecos no es un fallo del programa: es su resultado, y convertirlo en un
código distinto haría que un guion lo tratara como avería.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from adaptadores.salientes.biblioteca.catalogo import CatalogoDeFuentes
from adaptadores.salientes.biblioteca.inventario import auditar, como_texto

#: La marca de rango que las transcripciones llevan dentro: «[Pagina 88 a 99 del
#: libro]». `FUENTES.md` §Lo que falta la documenta para `PIS` y `SPI`. Es la
#: única fuente de páginas que una parte trae consigo; lo demás sería estimar.
_RANGO_EN_LA_PARTE = re.compile(
    r"\[\s*P[áa]gina\s+(\d+)\s+a\s+(\d+)\s+del\s+libro\s*\]", re.I
)


def _raiz_del_corpus() -> Path:
    return Path(__file__).resolve().parents[3] / "contenido" / "corpus"


def _proponer_partes(raiz: Path) -> int:
    """Enumera `_obras-md/` y propone filas para `PARTES.md`. No escribe."""
    catalogo = CatalogoDeFuentes.desde_directorio(raiz)
    obras_md = raiz / "_obras-md"
    if not obras_md.is_dir():
        print(f"No existe {obras_md}.")
        print(
            "Es lo esperado en un clon del repositorio: `.gitignore` excluye las\n"
            "obras desde `DD-15` para que retirarlas siga siendo posible. Pida al\n"
            "equipo el material y vuelva a ejecutar esto en un equipo que lo tenga.\n"
            "No se propone ninguna fila: inventarla sería inventar páginas."
        )
        return 0

    claves = {o.clave for o in catalogo.obras()}
    print("| Identificador | Obra | Título | Impresa inicial | Impresa final | Markdown | PDF |")
    print("|---|---|---|---:|---:|---|---|")
    propuestas = 0
    for directorio in sorted(p for p in obras_md.iterdir() if p.is_dir()):
        clave = directorio.name.upper()
        if clave not in claves:
            print(f"<!-- {directorio.name}: no es una clave de FUENTES.md; se omite -->")
            continue
        for archivo in sorted(directorio.glob("*.md")):
            try:
                texto = archivo.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:  # pragma: no cover
                print(f"<!-- {archivo.name}: no se pudo leer ({exc}) -->")
                continue
            rango = _RANGO_EN_LA_PARTE.search(texto)
            nombre = archivo.stem.lower()
            pdf = directorio / f"{archivo.stem}.pdf"
            if not rango:
                print(
                    f"<!-- {clave}:{nombre} · sin marca de rango dentro del archivo. "
                    f"La página se lee del escaneo y se escribe a mano: no se propone -->"
                )
                continue
            print(
                f"| {clave}:{nombre} | {clave} | (poner título) | "
                f"{rango.group(1)} | {rango.group(2)} | {archivo.name} | "
                f"{pdf.name if pdf.is_file() else '—'} |"
            )
            propuestas += 1
    print()
    print(f"<!-- {propuestas} filas propuestas. Revíselas contra la obra antes de pegarlas. -->")
    return 0


def principal(argumentos: list[str]) -> int:
    raiz = _raiz_del_corpus()
    if "--partes" in argumentos:
        return _proponer_partes(raiz)
    inventario = auditar(raiz)
    print(inventario.como_json() if "--json" in argumentos else como_texto(inventario))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal(sys.argv[1:]))
