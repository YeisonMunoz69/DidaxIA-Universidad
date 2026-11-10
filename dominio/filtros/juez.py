from __future__ import annotations

import re

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno


_CERTEZA_ABSOLUTA = re.compile(
    r"est[aá]\s+comprobado|sin\s+duda\s+es|definitivamente\s+es|"
    r"es\s+correcto\s+que|con\s+toda\s+certeza",
    re.IGNORECASE,
)

_PATRON_REFERENCIA = re.compile(r"\{\{\s*[A-Za-z0-9_-]+\s*\}\}")

_INTERROGACION = re.compile(r"[¿?]")


def _prosa_sin_referencias(respuesta: str) -> str:
    return _PATRON_REFERENCIA.sub(" ", respuesta)

class FiltroJuez(Filtro):

    nombre = "juicio complementario"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        advertencias: list[str] = []

        prosa = _prosa_sin_referencias(ctx.respuesta)
        hallazgo = _CERTEZA_ABSOLUTA.search(prosa)
        if hallazgo:
            advertencias.append(
                f"lenguaje de certeza absoluta en la prosa: «{hallazgo.group(0)}» "
                f"(ERS-01 §6.4: ninguna decisión crítica se delega al generador)"
            )

        if ctx.nivel_divulgacion == 1 and not _INTERROGACION.search(ctx.respuesta):
            advertencias.append(
                "nivel «sondeo» sin ninguna interrogación: el contrato exige "
                "formular una pregunta"
            )

        meta = {
            "advertencias": tuple(advertencias),
            "aprobado_por_el_juez": not advertencias,
        }

        return ctx, meta
