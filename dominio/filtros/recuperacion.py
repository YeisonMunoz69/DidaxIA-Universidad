"""
recuperacion.py — Filtro 5 · recuperación filtrada por nodo
============================================================

`ADR-001` §6.3 lo sitúa en la **ruta caliente** y lo justifica con `RF-RAG-09` y
`RF-GPE-13`: lo recuperado condiciona la respuesta del turno, así que no puede
ocurrir en frío.

El filtro **no recupera**: pide al puerto y deja constancia. Toda la estrategia
—la jerarquía de `ADR-002`, el umbral de `ADR-006`— vive detrás del puerto,
que es lo que permite cambiar de almacén sin tocar la cadena.

Lo que sí es suyo, y por eso está aquí y no en el adaptador
-----------------------------------------------------------
**Dejar registrado que el turno operó en modo sin fuente.** `ADR-006` U3 encadena
tres consecuencias a esa condición: no se inyecta contexto, la respuesta se marca
con confianza reducida y **la verificación pasa a obligatoria**. Las tres las
ejercen filtros posteriores, y ninguno puede saberlo si el turno no lo lleva
escrito. Que el contexto lo diga no es telemetría: es el mecanismo.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.puertos.corpus import PuertoCorpus


class FiltroRecuperacion(Filtro):
    """Filtro 5 de `ADR-001` §6.3."""

    nombre = "recuperación filtrada por nodo"
    ruta = "caliente"

    def __init__(self, corpus: PuertoCorpus, k: int = 3) -> None:
        self._corpus = corpus
        self._k = k

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        recuperacion = self._corpus.recuperar(
            ctx.texto_estudiante,
            nodo=ctx.nodo_activo or None,
            k=self._k,
        )

        # La traza lleva las similitudes además del recuento. `ADR-006` U5 dejó
        # escrito que la calibración del umbral necesita **la distribución de
        # puntuaciones de aciertos frente a fallos**, y que el instrumento de E01
        # no las volcaba. Registrarlas desde el primer turno evita repetir ese
        # hallazgo: el dato que hará falta en el objetivo 4 se recoge ahora, que
        # es cuando cuesta nada.
        meta = {
            "fragmentos": len(recuperacion.fragmentos),
            "similitudes": [round(s, 4) for s in recuperacion.similitudes],
            "sin_fuente": recuperacion.sin_fuente,
            "nodo_activo": ctx.nodo_activo,
        }
        return replace(ctx, recuperacion=recuperacion), meta
