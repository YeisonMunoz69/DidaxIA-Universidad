"""Arbitraje pedagógico · el filtro 6 de `ADR-001` §6.3.

Dos cosas viven aquí y **no son la misma**, aunque el filtro sea uno:

- **Cuánto se revela** — la escala de divulgación de tres niveles de
  `RF-GEN-05`. Está en `divulgacion.py` y la escribió `PM-B05`.
- **Qué se hace** — la jerarquía de intervención de la tensión `T6`: bloqueo
  sin intento, ciclo negativo, autoeficacia, ansiedad explícita,
  autorregulación por defecto. Está en `intervencion.py` y la escribió
  `PM-B13`, con la errata `E-01` ya aplicada (el defecto va en el nivel 5, no
  en el 4).

Separarlas es lo que permite que la primera funcione sin la segunda, que fue
la situación hasta `PM-B13`: el sistema ya sabía cuánto revelar antes de saber
elegir entre las cinco intervenciones.
"""

from dominio.arbitraje.divulgacion import (
    CORRECCION,
    NOMBRE,
    PISTA,
    SONDEO,
    Decision,
    Señales,
    decidir,
)
from dominio.arbitraje.intervencion import (
    ANSIEDAD_EXPLICITA,
    AUTOEFICACIA_BAJA,
    AUTORREGULACION,
    BLOQUEO_SIN_INTENTO,
    CICLO_NEGATIVO,
    NOMBRE_INTERVENCION,
    DecisionIntervencion,
    decidir_intervencion,
)

__all__ = [
    "ANSIEDAD_EXPLICITA",
    "AUTOEFICACIA_BAJA",
    "AUTORREGULACION",
    "BLOQUEO_SIN_INTENTO",
    "CICLO_NEGATIVO",
    "CORRECCION",
    "Decision",
    "DecisionIntervencion",
    "NOMBRE",
    "NOMBRE_INTERVENCION",
    "PISTA",
    "SONDEO",
    "Señales",
    "decidir",
    "decidir_intervencion",
]
