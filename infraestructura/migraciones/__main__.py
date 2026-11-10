"""CLI deliberadamente limitado al laboratorio efímero de la sesión 2A."""

from __future__ import annotations

import argparse
import sys

from adaptadores.salientes.conexion import conectar
from infraestructura.migraciones.catalogo import CatalogoInvalido
from infraestructura.migraciones.ejecutor import ErrorDeMigracion, ejecutar
from pruebas.soporte.guarda_bd_pruebas import BaseNoEsDePruebas, exigir_base_de_pruebas


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar el PostgreSQL efímero de DidaxIA")
    parser.add_argument(
        "--adoptar-existente",
        action="store_true",
        help="registrar un prefijo 01–10 ya presente después de verificar su forma",
    )
    args = parser.parse_args()

    try:
        cadena = exigir_base_de_pruebas()
        with conectar(cadena) as conexion:
            resultado = ejecutar(conexion, adoptar_existente=args.adoptar_existente)
    except (BaseNoEsDePruebas, CatalogoInvalido, ErrorDeMigracion) as exc:
        print(f"Migración detenida: {exc}", file=sys.stderr)
        return 2

    print(
        "Migraciones correctas · "
        f"adoptadas={list(resultado.adoptadas)} aplicadas={list(resultado.aplicadas)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
