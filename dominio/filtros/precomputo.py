"""
precomputo.py — Filtro 6.5 · el desarrollo llega al generador ya hecho
=========================================================================

`ADR-013` §6.2 sitúa este filtro **después del arbitraje (6) y antes de la
construcción del prompt (7)**: el filtro 7 no puede empezar sin él —
`FiltroPrompt._orientacion` ya lee `ctx.precomputo` desde que `PM-B17`
cableó `ADR-014`, así que este filtro es lo único que faltaba para que ese
campo dejara de estar siempre vacío.

Cuándo precomputa, y por qué no siempre
------------------------------------------
`ADR-008` P1 es la condición exacta: *«cuando el filtro 2 clasifica la
intención como procedimental y el filtro 1 entregó una expresión
normalizada, el motor simbólico calcula el resultado antes de generar»*.
Fuera de esa condición no hay nada que precomputar —una consulta conceptual
o emocional no trae una expresión que derivar— y el filtro lo deja dicho en
la traza en vez de callarlo, la misma disciplina que la compuerta del
filtro 4 ya sigue con la recuperación.

Qué expresión, y la limitación que se declara a propósito
--------------------------------------------------------------
`ctx.expresiones` es una tupla — el filtro 1 puede segmentar más de una por
turno — y este filtro precomputa **solo la primera**. `ADR-013` habla del
desarrollo de «la expresión» en singular en todos sus ejemplos, y extenderlo
a varias es una ampliación que nadie ha medido ni pedido: se declara aquí en
vez de adivinarla.

Qué NO decide este filtro
-----------------------------
No decide **qué se revela**: el precómputo completo entra en `ctx.precomputo`
y es `FiltroPrompt` quien lo trunca al nivel que `FiltroArbitraje` ya fijó
(`ADR-013` §7.3, mitigación de `R-22`). Un filtro que truncara aquí
duplicaría esa decisión en dos sitios.

Límite o derivada, y quién lo decide · `PM-B24`
----------------------------------------------------
Hasta el 2026-08-11 este filtro solo pedía la **derivada**: nada en la cadena
distinguía una petición de límite de una de derivada en el texto del
estudiante, y `ADR-013` §9.bis había aplazado adelantar esa señal al filtro 4
(`D-10`) — pero nunca dijo que el filtro **2** no pudiera reconocerla con su
propia cascada léxica, que es donde vive la clasificación de intención.

`dominio/filtros/intencion.py` ahora deja `ctx.es_limite` y, cuando pudo
extraer las dos mitades, `ctx.limite_expresion` y `ctx.limite_destino`. Este
filtro los lee **antes** que `ctx.expresiones`: si hay límite reconocido,
pide `puerto.precomputar_limite()`; si no, sigue el camino de siempre.
**Nunca los dos a la vez** — `RF-IUC-03` pide llegar al desarrollo del
límite, no a los dos desarrollos de la misma expresión.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, runtime_checkable

from dominio.filtros.base import Filtro
from dominio.modelo.matematica import Precomputo
from dominio.modelo.referencias_matematicas import sustituir_variable
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.estrategias import CAMBIO_DE_REPRESENTACION
from dominio.pedagogia.intenciones import familia_de


@runtime_checkable
class _PuertoDePrecomputo(Protocol):
    """Lo único de `PuertoSimbolico` (y su capacidad de límite, `PM-B22`) que
    este filtro necesita.

    Declarado aparte —en vez de importar el puerto completo— porque este
    filtro no verifica: acoplarlo a `verificar()` también le daría una
    responsabilidad que no le corresponde ejercer.
    """

    def precomputar(
        self, expresion: str, variable: str = "x", orden: int = 1, notacion: str = ""
    ) -> Precomputo: ...
    def precomputar_limite(
        self, expresion: str, variable: str = "x", valor_limite: str = "0"
    ) -> Precomputo: ...
    def precomputar_valor(self, expresion: str) -> Precomputo: ...


class FiltroPrecomputo(Filtro):
    """Filtro 6.5 de `ADR-013` §6.2."""

    nombre = "precómputo simbólico"
    ruta = "caliente"

    def __init__(self, puerto_simbolico: _PuertoDePrecomputo) -> None:
        self._cas = puerto_simbolico

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if ctx.continuidad is not None and (ctx.continuidad.get("aclaracion") or not ctx.ejercicio_activo):
            return ctx, {"precomputado": False, "motivo": "operación o referente pendiente; no se asume derivada"}
        # La FAMILIA, no la clase: las siete clases procedimentales del
        # catálogo v1 comparten que hay algo que calcular. Ver
        # `dominio/pedagogia/intenciones.py::familia_de`.
        familia = familia_de(ctx.intencion)
        pide_representacion = bool(
            ctx.intencion_detalle
            and ctx.intencion_detalle.estrategia_solicitada == CAMBIO_DE_REPRESENTACION
        )
        if familia not in ("procedimental", "ambigua", "") and not pide_representacion:
            return ctx, {
                "precomputado": False,
                "motivo": f"intención {ctx.intencion} ({familia}) no requiere precómputo",
            }

        if ctx.es_limite and ctx.limite_expresion:
            return self._precomputar_limite(ctx)

        activo = ctx.ejercicio_activo or {}
        if activo.get("tipo") == "valor_derivada":
            derivada = self._cas.precomputar(activo["expresion"], variable=activo.get("variable", "x"), orden=activo.get("orden", 1))
            evaluada = sustituir_variable(derivada.resultado_corriente, activo.get("variable", "x"), activo["destino"]) if derivada.ok else ""
            resultado = self._cas.precomputar_valor(evaluada) if evaluada else derivada
            return replace(ctx, precomputo=resultado), {
                "precomputado": True, "tipo": "valor_derivada", "expresion": activo["expresion"],
                "destino": activo["destino"], "expresion_evaluada": evaluada,
                "ok": resultado.ok, "error": resultado.error,
            }
        if activo.get("tipo") == "valor":
            resultado = self._cas.precomputar_valor(activo["expresion"])
            return replace(ctx, precomputo=resultado), {
                "precomputado": True, "tipo": "valor", "expresion": activo["expresion"],
                "ok": resultado.ok, "error": resultado.error,
            }
        expresion = (
            activo.get("expresion") if activo.get("tipo") == "derivada" else None
        ) or (ctx.expresiones[0] if ctx.expresiones else ctx.expresion_previa)
        if not expresion:
            return ctx, {"precomputado": False, "motivo": "no hay expresión matemática disponible"}

        nuevo, meta = self._precomputar_derivada(ctx, expresion)
        if pide_representacion:
            meta["motivo"] = "la persona pidió una representación gráfica explícita"
        return nuevo, meta

    def _precomputar_derivada(self, ctx: ContextoTurno, expresion: str | None = None) -> tuple[ContextoTurno, dict]:
        expr = expresion or (ctx.expresiones[0] if ctx.expresiones else "")
        if not expr:
            return ctx, {"precomputado": False, "motivo": "no hay expresión matemática"}
        # `PM-B32`: la notación que el estudiante eligió viaja hasta aquí y no
        # se interpreta por el camino. Vacía = no eligió, y decide el motor.
        resultado = self._cas.precomputar(
            expr, variable=(ctx.ejercicio_activo or {}).get("variable", "x"), orden=(ctx.ejercicio_activo or {}).get("orden", 1), notacion=ctx.notacion
        )

        meta = {
            "precomputado": True,
            "tipo": "derivada",
            "expresion": expr,
            "ok": resultado.ok,
            "pasos": len(resultado.pasos),
            "regla_critica": resultado.regla_critica,
            "concepciones_candidatas": resultado.concepciones_candidatas,
        }
        if not resultado.ok:
            meta["error"] = resultado.error
        if len(ctx.expresiones) > 1:
            meta["expresiones_descartadas"] = ctx.expresiones[1:]

        return replace(ctx, precomputo=resultado), meta

    def _precomputar_limite(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        resultado = self._cas.precomputar_limite(
            ctx.limite_expresion, variable=ctx.limite_variable, valor_limite=ctx.limite_destino
        )
        meta = {
            "precomputado": True,
            "tipo": "limite",
            "expresion": ctx.limite_expresion,
            "destino": ctx.limite_destino,
            "variable": ctx.limite_variable,
            "ok": resultado.ok,
            "pasos": len(resultado.pasos),
        }
        if not resultado.ok:
            meta["error"] = resultado.error
        return replace(ctx, precomputo=resultado), meta
