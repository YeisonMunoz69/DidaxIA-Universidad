"""
supervision.py — Reexportación de compatibilidad · `RU-12`
===============================================================

**Este archivo ya no define nada.** Hasta la Fase 2 · sesión 3 contenía los
estados, los tipos, los modelos `ItemDeRevision`/`NuevoItem` y el almacén en
memoria `ColaDeRevision`, y el adaptador de PostgreSQL
(`adaptadores/salientes/registro/cola_revision_db.py`) los importaba **desde
aquí**: un adaptador saliente dependiendo de uno entrante, la dirección que
`ADR-001` §7.2 prohíbe.

Dónde vive ahora cada cosa:

- `ESTADO_*` y `TIPO_*` — `dominio/puertos/supervision.py`
- `ItemDeRevision` y `NuevoItem` — `dominio/puertos/supervision.py`
- `ColaDeRevision` (memoria) — `adaptadores/salientes/registro/cola_revision_memoria.py`
- el contrato — `dominio/puertos/supervision.py::PuertoColaDeRevision`

Se conserva esta reexportación explícita —y no se borra el módulo— porque esta
ruta está citada en documentación gobernada que la sesión 3 no puede editar. Es
un puente, no una segunda definición: aquí no hay nada declarado.

No confundir con `adaptadores/entrantes/http/rutas/supervision.py`, que son las
cuatro rutas de `RU-12`.


"""

from __future__ import annotations

from adaptadores.salientes.registro.cola_revision_memoria import ColaDeRevision
from dominio.puertos.supervision import (
    ESTADO_APROBADO,
    ESTADO_EDITADO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    TIPO_DEGRADADO,
    TIPO_RESPUESTA,
    TIPO_SIN_FUENTE,
    ItemDeRevision,
    NuevoItem,
    PuertoColaDeRevision,
)

__all__ = [
    "ESTADO_APROBADO",
    "ESTADO_EDITADO",
    "ESTADO_PENDIENTE",
    "ESTADO_RECHAZADO",
    "TIPO_DEGRADADO",
    "TIPO_RESPUESTA",
    "TIPO_SIN_FUENTE",
    "ColaDeRevision",
    "ItemDeRevision",
    "NuevoItem",
    "PuertoColaDeRevision",
]
