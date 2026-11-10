"""Relectura acotada y reanudable. Sin --aplicar sólo cuenta pendientes, sin IA.

python -m infraestructura.operacion.reanalizar_factores --actor SUJETO_ADMIN
    --desde 2026-09-01T00:00:00-05:00 --hasta 2026-10-04T00:00:00-05:00
    [--clase UUID] [--aplicar --maximo-llamadas 10]
La conexión y clave se resuelven del entorno; nunca se imprimen.
"""

import argparse
import json
import os
from datetime import datetime

from adaptadores.salientes.registro.relectura_factores import ejecutar, entrada_historica

__all__ = ["ejecutar", "entrada_historica"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actor", required=True)
    p.add_argument("--desde", required=True, type=datetime.fromisoformat)
    p.add_argument("--hasta", required=True, type=datetime.fromisoformat)
    p.add_argument("--clase")
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--maximo-llamadas", type=int, default=10)
    a = p.parse_args()
    if a.desde.tzinfo is None or a.hasta.tzinfo is None:
        p.error("las fechas requieren zona horaria")
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        p.error("falta AGENTE_BD")
    try:
        print(
            json.dumps(
                ejecutar(
                    cadena,
                    actor=a.actor,
                    desde=a.desde,
                    hasta=a.hasta,
                    clase=a.clase,
                    aplicar=a.aplicar,
                    maximo_llamadas=a.maximo_llamadas,
                ),
                ensure_ascii=False,
            )
        )
    except Exception as exc:  # noqa: BLE001 — no imprime cadenas de conexión ni contenido
        p.exit(1, f"Relectura interrumpida ({type(exc).__name__}); no se imputaron ceros.\n")


if __name__ == "__main__":
    main()
