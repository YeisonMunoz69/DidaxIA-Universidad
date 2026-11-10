"""Adaptadores del puerto de recuperación de contexto · `ADR-010`.

Tres piezas y conviene no confundir sus estados:

- `grafo.py` — el grafo pedagógico en memoria, desde su definición versionada.
  **Funciona y está probado.**
- `jerarquico.py` — la configuración D de `ADR-002` sobre índice y grafo.
  **Funciona y está probado.**
- `indice.py` — los contratos de índice y codificador, y una implementación
  **en memoria que es doble de pruebas**, no el almacén del sistema.
- `indice_postgres.py` — el almacén de `ADR-010`, con `psycopg` y SQL propio
  según `DD-19`. **Escrito, y sus pruebas se saltan solas si no hay base.**

⚠️ **Ninguna cifra que salga de este paquete mide calidad de recuperación.** El
doble en memoria usa similitud léxica y el codificador de las pruebas es de
juguete. La calidad la midió `E01` con `intfloat/multilingual-e5-base`, y sigue
siendo la única medición que dice algo al respecto.

**Y falta el codificador real.** `IndicePostgres` recibe uno; el que carga el
modelo no está escrito, así que hoy nada codifica de verdad.
"""

from adaptadores.salientes.recuperacion.grafo import GrafoEnMemoria, Nodo
from adaptadores.salientes.recuperacion.indice import (
    DIMENSION,
    Codificador,
    Indice,
    IndiceEnMemoria,
)
from adaptadores.salientes.recuperacion.indice_postgres import IndicePostgres
from adaptadores.salientes.recuperacion.jerarquico import (
    K_ADOPTADO,
    MARGEN_INICIAL,
    UMBRAL_INICIAL,
    PerfilLexico,
    RecuperadorJerarquico,
)

__all__ = [
    "DIMENSION",
    "Codificador",
    "GrafoEnMemoria",
    "Indice",
    "IndiceEnMemoria",
    "IndicePostgres",
    "K_ADOPTADO",
    "MARGEN_INICIAL",
    "Nodo",
    "PerfilLexico",
    "RecuperadorJerarquico",
    "UMBRAL_INICIAL",
]
