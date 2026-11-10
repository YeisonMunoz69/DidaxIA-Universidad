"""
generacion.py — Filtro 8 · generación
=====================================

`ADR-001` §6.3 lo pone en la **ruta caliente**: es la llamada al modelo, y su
latencia es la que más pesa en el presupuesto de `RNF-EFI-01`. El filtro **no
genera**: pide al puerto `dominio.puertos.generacion` y deja constancia, igual
que el filtro 5 pide al puerto de corpus. Qué proveedor hay detrás es asunto del
adaptador, y por eso este filtro recibe el puerto por inyección y **nunca importa
un adaptador**: hacerlo cruzaría la frontera que la regla N1 vigila.

Lo que es suyo, y por eso está aquí y no en el adaptador
-------------------------------------------------------
**Dejar en la traza la procedencia de lo generado.** `RF-REG-04` pide latencia y
unidades desagregadas por componente, y sin saber qué modelo respondió no se
puede atribuir un fallo. El adaptador rellena `modelo`, `proveedor` y
`unidades_*`; este filtro los copia a la traza del turno.

**Guardar la generación como lo que es: sin verificar.** Va a `ctx.generacion` y
no a `ctx.respuesta`, porque `ADR-008` pone la verificación dos filtros más
adelante y la respuesta del sistema es lo que sale de ahí, no de aquí.

Qué NO hace
-----------
**No reintenta ni respalda.** Si el puerto lanza `ErrorDeGeneracion`, se propaga
al orquestador, que es quien tiene la política de reintento y respaldo con su
traza —el puerto lo dice y `ADR-005` C4 lo reparte así—. Meter el reintento aquí
escondería latencia que `RNF-EFI-01` presupuesta.

**No juzga si la respuesta sirve.** Una generación vacía se guarda y se marca en
la traza; decidir qué hacer con ella es de un filtro posterior.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.puertos.generacion import (
    ErrorDeGeneracion,
    PeticionDeGeneracion,
    PuertoGeneracion,
    RespuestaDeGeneracion,
)


class FiltroGeneracion(Filtro):
    """Filtro 8 de `ADR-001` §6.3."""

    nombre = "generación"
    ruta = "caliente"

    def __init__(
        self,
        generador: PuertoGeneracion,
        *,
        temperatura: float = 0.0,
        maximo_de_unidades: int = 800,
    ) -> None:
        """`temperatura` y `maximo_de_unidades` son configurables pero por defecto
        son los reproducibles del puerto: `T4` fijó no ajustar el generador en la
        v1 y apoyarse en aprendizaje en contexto, de modo que un turno tiene que
        poder reconstruirse (`RF-ORQ-14`). El techo de unidades lo impone el
        presupuesto de latencia de `RNF-EFI-01`, no la estética."""
        self._generador = generador
        self._temperatura = temperatura
        self._maximo = maximo_de_unidades

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if ctx.continuidad is not None and ctx.continuidad.get("aclaracion"):
            respuesta = RespuestaDeGeneracion("aclaración del referente", estructura={
                "narracion": ctx.continuidad["aclaracion"], "nivel": 1, "afirmaciones": [], "citadas": [],
            })
            return replace(ctx, generacion=respuesta, nivel_divulgacion=1), {"proveedor": "local", "razon_de_parada": "aclaracion_de_tarea"}
        if ctx.resultado_verificado or ctx.transformacion_verificada:
            # El cierre sale de afirmaciones del CAS y volverá a pasar por el
            # filtro 9. No hace falta pedir a un modelo que rehaga una
            # comprobación ya ganada ni depender de su disponibilidad.
            return ctx, {
                "modelo": "sympy", "proveedor": "local", "unidades_de_entrada": 0,
                "unidades_de_salida": 0, "vacia": False,
                "razon_de_parada": (
                    "cierre_matematico_verificado" if ctx.resultado_verificado
                    else "transformacion_matematica_verificada"
                ),
            }
        try:
            respuesta = self._generador.generar(
                PeticionDeGeneracion(
                    instruccion=ctx.prompt,
                    temperatura=self._temperatura,
                    maximo_de_unidades=self._maximo,
                    mensajes=ctx.mensajes_generacion,
                )
            )
        except ErrorDeGeneracion:
            if ctx.continuidad is not None and ctx.siguiente_objetivo:
                return ctx, {"vacia": True, "razon_de_parada": "proveedor_fallo; objetivo_verificable_disponible"}
            if ctx.continuidad is not None and ctx.continuidad.get('activa') and ctx.retroalimentacion_del_intento is None:
                respaldo = RespuestaDeGeneracion('aviso recuperable', estructura={
                    'narracion': 'La explicación automática no está disponible en este momento. '
                        'Conservo el ejercicio y los pasos comprobados. Puedes continuar escribiendo tu procedimiento '
                        'o volver a pedir una explicación.',
                    'nivel': 1, 'afirmaciones': [], 'citadas': [],
                })
                return replace(ctx, generacion=respaldo), {
                    'proveedor': 'local', 'vacia': False, 'razon_de_parada': 'proveedor_fallo; continuidad_conservada',
                }
            if ctx.retroalimentacion_del_intento is None:
                raise
            return ctx, {"vacia": True, "razon_de_parada": "proveedor_fallo; base_comprobada_disponible"}

        # La traza lleva la procedencia y las unidades que `RF-REG-04` exige por
        # componente. No lleva el texto: la respuesta viaja en el contexto, y
        # duplicarla en la traza inflaría el registro sin añadir nada.
        meta = {
            "modelo": respuesta.modelo,
            "proveedor": respuesta.proveedor,
            "unidades_de_entrada": respuesta.unidades_de_entrada,
            "unidades_de_salida": respuesta.unidades_de_salida,
            "vacia": respuesta.vacia,
            "razon_de_parada": respuesta.metadatos.get("finish_reason", ""),
        }
        return replace(ctx, generacion=respuesta), meta
