from __future__ import annotations

from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.puertos.corpus import PuertoCorpus


class FiltroRecuperacion(Filtro):

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

        meta = {
            "fragmentos": len(recuperacion.fragmentos),
            "similitudes": [round(s, 4) for s in recuperacion.similitudes],
            "sin_fuente": recuperacion.sin_fuente,
            "nodo_activo": ctx.nodo_activo,
        }
        return replace(ctx, recuperacion=recuperacion), meta
