from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from adaptadores.salientes.corpus.cargador import cargar, claves_de_obra


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cargar los fragmentos del corpus en el índice.")
    p.add_argument(
        "--directorio",
        type=Path,
        default=AQUI / "contenido" / "corpus" / "fragmentos",
        help="dónde están los fragmentos (por defecto, contenido/corpus/fragmentos)",
    )
    p.add_argument(
        "--fuentes",
        type=Path,
        default=AQUI / "contenido" / "corpus" / "fuentes.json",
        help="el catálogo de obras (por defecto, contenido/corpus/fuentes.json)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="carga, reporta y NO escribe nada en el índice",
    )
    return p.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)

    obras = claves_de_obra(args.fuentes)
    resultado = cargar(args.directorio, obras=obras)

    print("=" * 74)
    print("INGESTA DEL CORPUS AL ÍNDICE")
    print("=" * 74)
    print(f"  directorio : {args.directorio}")
    print(f"  fuentes    : {args.fuentes} ({len(obras)} obras)")
    print(f"  leídos     : {len(resultado.fragmentos) + len(resultado.excluidos_por_dd02)}")
    print(f"  entran     : {len(resultado.fragmentos)}")
    print(f"  excluidos por DD-02 (sin marca `verificacion_dd02`): "
          f"{len(resultado.excluidos_por_dd02)}")
    for e in resultado.excluidos_por_dd02:
        print(f"    - {e}")

    if resultado.fallos:
        print(f"\n✗ {len(resultado.fallos)} fallo(s) de lectura. No se escribe nada:")
        for f in resultado.fallos:
            print(f"    - {f}")
        return 1

    if not resultado.fragmentos:

        print("\n✗ el corpus no contiene ningún fragmento admisible; no se inicia el backend.")
        return 1

    if args.dry_run:
        print(f"\n--dry-run: no se escribió nada. {len(resultado.fragmentos)} "
              f"fragmento(s) habrían entrado al índice.")
        return 0

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        print("\n✗ falta AGENTE_BD en el entorno: no hay a qué índice escribir.")
        return 1

    from adaptadores.salientes.recuperacion.codificador import CodificadorE5
    from adaptadores.salientes.recuperacion.indice_postgres import IndicePostgres

    print("\n  cargando el codificador (intfloat/multilingual-e5-base)…")
    indice = IndicePostgres(cadena, CodificadorE5())
    guardados = indice.guardar(resultado.fragmentos)

    print(f"\n✓ {guardados} fragmento(s) escritos en el índice (INSERT/UPDATE, "
          f"idempotente).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
