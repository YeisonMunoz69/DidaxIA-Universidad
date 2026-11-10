"""
clases.py — Reexportación de compatibilidad · `DD-12`
==========================================================

**Este archivo ya no define nada.** Hasta la Fase 2 · sesión 3 contenía los
modelos `Clase`/`Matricula` y el almacén en memoria `Clases`, y el adaptador
de PostgreSQL (`adaptadores/salientes/registro/clases_db.py`) importaba los
modelos **desde aquí**: un adaptador saliente dependiendo de uno entrante, la
dirección que `ADR-001` §7.2 prohíbe.

Dónde vive ahora cada cosa:

| Antes, aquí | Ahora |
|---|---|
| `Clase`, `Matricula` | `dominio/puertos/clases.py` |
| `Clases` (memoria) | `adaptadores/salientes/registro/clases_memoria.py` |
| el contrato | `dominio/puertos/clases.py::PuertoClases` |

Se conserva esta reexportación explícita —y no se borra el módulo— porque la
ruta `adaptadores/entrantes/http/clases.py` está citada en documentación
gobernada que esta sesión no puede editar. Es un puente, no una segunda
definición: aquí no hay ninguna clase declarada.

⚠️ No confundir con `adaptadores/entrantes/http/rutas/clases.py`, que son las
cinco rutas de `DD-12`.


"""

from __future__ import annotations

from adaptadores.salientes.registro.clases_memoria import Clases
from dominio.puertos.clases import Clase, Matricula, PuertoClases

__all__ = ["Clase", "Clases", "Matricula", "PuertoClases"]
