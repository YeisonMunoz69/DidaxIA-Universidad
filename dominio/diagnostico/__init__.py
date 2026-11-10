"""Diagnóstico conceptual de dos niveles · `S5` de `03-Plan-de-Construccion.md`.

`PM-B08`: el patrón *two-tier* de `RC-PED-06`/`RF-DGC-01` — turno de cálculo,
turno de razón, y la clasificación en los cuatro estados de `p-two-tier.md`
que `RF-DGC-03` exige distinguibles. Ver el docstring de `clasificador.py`
para qué prerrequisito lo desbloqueó y qué queda deliberadamente fuera.
"""

from dominio.diagnostico.clasificador import (
    ACIERTO_SIN_COMPRENSION,
    COMPRENSION,
    CONCEPCION_ERRONEA,
    ERROR_DE_EJECUCION,
    NOMBRE_ESTADO,
    Diagnostico,
    OpcionRazon,
    RespuestaDosNiveles,
    clasificar,
)

__all__ = [
    "ACIERTO_SIN_COMPRENSION",
    "COMPRENSION",
    "CONCEPCION_ERRONEA",
    "ERROR_DE_EJECUCION",
    "NOMBRE_ESTADO",
    "Diagnostico",
    "OpcionRazon",
    "RespuestaDosNiveles",
    "clasificar",
]
