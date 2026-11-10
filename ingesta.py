"""ingesta.py — Une el cargador de fragmentos con el índice

No es un comprobador: es la ingesta del sistema. Las dos mitades existían y
nadie las unía —`cargar()` en `adaptadores/salientes/corpus/cargador.py` y
`guardar()` en `adaptadores/salientes/recuperacion/indice_postgres.py`—, así
que el índice llevaba vacío desde que se escribió. Sin esto la recuperación
nunca se había ejercitado contra el corpus real: solo contra dobles.

Qué hace, en orden
-------------------

1. Lee `contenido/corpus/fragmentos/` con `cargar()`, contra el catálogo de
   `FUENTES.md`.
2. Descarta lo que `DD-02` bloquea: un fragmento sin la marca
   `verificacion_dd02` **no entra al índice**, y se cuenta y se nombra —nunca
   se salta en silencio—. Eso ya lo hace `cargar()`; aquí solo se informa.
3. Si algo quedó con un fallo de lectura (`r.fallos`), la ingesta **se
   detiene sin escribir nada**: indexar con fallos abiertos escondería el
   problema detrás de una carga que en apariencia funcionó.
4. Codifica y guarda con `CodificadorE5` e `IndicePostgres`. `guardar()` ya es
   `INSERT ... ON CONFLICT DO UPDATE`, así que correr esto dos veces no
   duplica — es una propiedad del adaptador, no de este script, y
   `pruebas/integracion/test_ingesta.py` lo comprueba contra la base real.

Uso
---

    cd OE3-Implementacion/codigo
    python ingesta.py --dry-run     # solo informa, no escribe
    python ingesta.py               # con AGENTE_BD en el entorno

Por qué necesita la base y el modelo, y por qué eso está bien
----------------------------------------------------------------
Esto **no** es una prueba: es la operación que da datos reales al sistema, y
`DD-20` solo exime de servicios externos a las pruebas de `pytest`. Este
guion sí los necesita, igual que el propio `compose.yaml` junto al que vive.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from adaptadores.salientes.corpus.cargador import cargar, claves_de_obra  # noqa: E402


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--directorio",
        type=Path,
        default=AQUI / "contenido" / "corpus" / "fragmentos",
        help="dónde están los fragmentos (por defecto, contenido/corpus/fragmentos)",
    )
    p.add_argument(
        "--fuentes",
        type=Path,
        default=AQUI / "contenido" / "corpus" / "FUENTES.md",
        help="el catálogo de obras (por defecto, contenido/corpus/FUENTES.md)",
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
        # En el despliegue este programa es una barrera previa al backend.
        # Salir con éxito ante un corpus vacío volvería a declarar listo el
        # mismo estado que deja todas las respuestas «sin material».
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

    # Importados aquí y no arriba: arrastran `sentence-transformers` y
    # `psycopg`, y --dry-run no debería exigir ninguno de los dos para
    # informar qué entraría. Mismo patrón que `codificador.py` e
    # `indice_postgres.py`.
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
