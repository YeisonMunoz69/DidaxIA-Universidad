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

    def precomputar(
        self, expresion: str, variable: str = "x", orden: int = 1, notacion: str = ""
    ) -> Precomputo: ...
    def precomputar_limite(
        self, expresion: str, variable: str = "x", valor_limite: str = "0"
    ) -> Precomputo: ...
    def precomputar_valor(self, expresion: str) -> Precomputo: ...

class FiltroPrecomputo(Filtro):

    nombre = "precómputo simbólico"
    ruta = "caliente"

    def __init__(self, puerto_simbolico: _PuertoDePrecomputo) -> None:
        self._cas = puerto_simbolico

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if ctx.continuidad is not None and (ctx.continuidad.get("aclaracion") or not ctx.ejercicio_activo):
            return ctx, {"precomputado": False, "motivo": "operación o referente pendiente; no se asume derivada"}

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
