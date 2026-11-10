"""
plantillas/ — El adaptador que lee el andamiaje socrático (`PM-B06`)

- `cargador.py` — `CargadorDePlantillas`, que sirve `contenido/plantillas/`
  como `dominio.puertos.plantillas.PuertoPlantillas`.
- `items.py` — la otra lectura del mismo directorio: el ítem de dos niveles de
  `p-two-tier.md`, con sus cuatro razones tipificadas (`PM-B08`). Ahí vive
  también el puente de notación LaTeX → notación corriente, que es la parte
  frágil y está declarada como tal.

`contenido/plantillas/` es del carril de contenido (`PM-C14`, Fabián): aquí se
LEE y no se escribe, igual que `recuperacion/` hace con el grafo y el corpus.
"""

from adaptadores.salientes.plantillas.cargador import CargadorDePlantillas

__all__ = ["CargadorDePlantillas"]
