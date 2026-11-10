"""Adaptadores de persistencia del borde y del puerto de registro.

Del puerto de registro (`dominio/puertos/registro.py`):

- `postgres.py` — `AdaptadorPerfilPostgres`, persistencia versionada de los
  tres registros de `ADR-003` §6.2 sobre PostgreSQL (`PM-B11`, `RF-REG-02`).
- `archivo.py` — `AdaptadorRegistroArchivo`, el turno completo como archivo
  con fila de referencia (`DD-08`, `PM-B20`, `RF-REG-03` a `RF-REG-07`).
- `historial.py` — `AdaptadorHistorialPostgres`, `registrar_turno`
  (`RF-REG-01`) más las dos lecturas del borde (`PM-B37`).

De los tres contratos de borde consolidados en la Fase 2 · sesión 3, cada uno
con dos implementaciones del mismo puerto:

| Contrato | Memoria | PostgreSQL |
|---|---|---|
| `dominio/puertos/clases.py` | `clases_memoria.py` | `clases_db.py` |
| `dominio/puertos/supervision.py` | `cola_revision_memoria.py` | `cola_revision_db.py` |
| `dominio/puertos/rol_docente.py` | `solicitudes_docente_memoria.py` | `solicitudes_docente_db.py` |
| `dominio/puertos/consentimiento.py` | `consentimiento_degradado.py` (no guarda) | `consentimiento_db.py` |

`consentimiento_degradado.py` no es un almacén en memoria: no guarda nada, a
propósito, para reproducir exactamente lo que ocurría sin `AGENTE_BD`. Ver su
docstring.

Este `__init__` sigue exportando solo los dos nombres que ya exportaba; los
demás se importan por su módulo para no cargar adaptadores que no hagan falta.
"""

from adaptadores.salientes.registro.archivo import AdaptadorRegistroArchivo
from adaptadores.salientes.registro.postgres import AdaptadorPerfilPostgres

__all__ = ["AdaptadorPerfilPostgres", "AdaptadorRegistroArchivo"]
