"""
simbolico.py — Puerto de cálculo simbólico
==========================================

`ADR-001` §6.2 declara siete puertos y **no crea puertos especulativos**. Este
es el de verificación simbólica, con **dos operaciones** sobre el mismo
adaptador, según `ADR-013` §6.1:

| Operación | Filtro | Para qué |
|---|:--:|---|
| `precomputar` | 6.5 | El desarrollo llega al generador ya hecho |
| `verificar`   | 9   | Ninguna afirmación se emite sin comprobar |

**Por qué el mismo puerto y no dos.** Las dos operaciones tienen la misma
naturaleza —cálculo determinista, sin red, reproducible— y las mismas
condiciones de aislamiento de `RI-08`. Separarlas duplicaría la frontera de
proceso, que es el componente caro.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from dominio.modelo.matematica import (
    BloqueVerificable,
    InformeVerificacion,
    Precomputo,
)


@runtime_checkable
class PuertoSimbolico(Protocol):
    """Contrato del motor de álgebra computacional.

    El dominio depende de esta interfaz. Sustituir el motor consiste en
    escribir otra implementación; ningún filtro cambia.
    """

    def precomputar(
        self,
        expresion: str,
        variable: str = "x",
        orden: int = 1,
        notacion: str = "",
    ) -> Precomputo:
        """Desarrolla la derivada con la regla etiquetada en cada paso.

        ⚠️ El resultado **no se emite al estudiante**: entra al contexto del
        generador (`ADR-013` §2).

        `notacion` es **la que el estudiante eligió** (`D-21`, `PM-B32`), y va
        vacía cuando no eligió: el adaptador decide entonces, que es quien
        sabe qué notaciones tiene escritas. El dominio transporta la
        preferencia y no la interpreta — el mismo reparto que con `variable`.

        ⚠️ Y desde `PM-B31` esto **sí puede acabar en la pantalla**: cuando el
        generador falla en nivel 3, `D-21` manda emitir este desarrollo tal
        cual. Por eso la notación importa aquí y no solo en el prompt.
        """
        ...

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion:
        """Comprueba **todas** las afirmaciones declaradas.

        Barrido exhaustivo, con veredicto por defecto **desfavorable**:
        `ADR-008` V1.
        """
        ...
