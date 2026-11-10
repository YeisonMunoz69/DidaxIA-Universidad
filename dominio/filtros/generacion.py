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

    nombre = "generación"
    ruta = "caliente"

    def __init__(
        self,
        generador: PuertoGeneracion,
        *,
        temperatura: float = 0.0,
        maximo_de_unidades: int = 800,
    ) -> None:

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

        meta = {
            "modelo": respuesta.modelo,
            "proveedor": respuesta.proveedor,
            "unidades_de_entrada": respuesta.unidades_de_entrada,
            "unidades_de_salida": respuesta.unidades_de_salida,
            "vacia": respuesta.vacia,
            "razon_de_parada": respuesta.metadatos.get("finish_reason", ""),
        }
        return replace(ctx, generacion=respuesta), meta
