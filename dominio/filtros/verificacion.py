from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import CORRECCION
from dominio.filtros.base import Filtro
from dominio.modelo.matematica import InformeVerificacion
from dominio.modelo.respuesta import RespuestaGenerada, RespuestaMalformada
from dominio.modelo.turno import ContextoTurno


class FiltroVerificacion(Filtro):

    nombre = "verificación simbólica"
    ruta = "caliente"

    def __init__(self, puerto_simbolico, respuesta: RespuestaGenerada | None = None):
        self._cas = puerto_simbolico
        self._respuesta = respuesta

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if ctx.transformacion_verificada and self._respuesta is None:
            orientacion = RespuestaGenerada.desde_transformacion_verificada(ctx)
            if orientacion is not None and not orientacion.problemas():
                informe = self._cas.verificar(orientacion.bloques())
                if informe.aprobada:
                    return replace(
                        ctx, respuesta=orientacion.narracion,
                        respuesta_generada=orientacion, informe=informe,
                        nivel_divulgacion=2,
                    ), {
                        "resultado": "transformación intermedia comprobada",
                        "afirmaciones": len(informe.verificaciones),
                        "descendido": False,
                    }
        if ctx.resultado_verificado and self._respuesta is None:
            cierre = RespuestaGenerada.desde_acierto_verificado(ctx)
            if cierre is not None and not cierre.problemas():
                informe_cierre = self._cas.verificar(cierre.bloques())
                if informe_cierre.aprobada:
                    return replace(
                        ctx, respuesta=cierre.narracion,
                        respuesta_generada=cierre, informe=informe_cierre,
                        nivel_divulgacion=3,
                    ), {
                        "resultado": "retroalimentación de acierto comprobado",
                        "afirmaciones": len(informe_cierre.verificaciones),
                        "descendido": False,
                        "pasos_del_motor": len(ctx.precomputo.pasos) if ctx.precomputo else 0,
                    }
        respuesta = self._respuesta
        meta_origen: dict = {}

        if respuesta is None:
            respuesta, meta_origen = self._del_turno(ctx)

        if respuesta is None:

            return replace(ctx, nivel_divulgacion=1), {
                "resultado": "sin respuesta que verificar",
                "descendido": True,
                **meta_origen,
            }

        problemas = respuesta.problemas()
        if problemas:
            podada = respuesta.podada()
            return self._descender(ctx, podada), {
                "resultado": "contrato incumplido",
                "motivos": problemas,
                "descendido": True,
                **meta_origen,
            }

        informe = self._cas.verificar(respuesta.bloques())

        if informe.nada_que_verificar:
            return self._sin_afirmaciones(ctx, respuesta, informe, meta_origen)

        if not informe.aprobada:
            respaldo = self._respaldo(ctx, respuesta) or self._consulta_comprobada(ctx, respuesta, informe)
            if respaldo is not None:
                return respaldo
            podada = respuesta.podada()
            return self._descender(ctx, podada, informe), {
                "resultado": "verificación no superada",
                "motivo": informe.motivo_de_rechazo,
                "afirmaciones": len(informe.verificaciones),
                "descendido": True,
                **meta_origen,
            }

        nuevo = replace(
            ctx,
            respuesta=respuesta.narracion,
            respuesta_generada=respuesta,
            informe=informe,
            nivel_divulgacion=respuesta.nivel_divulgacion,
        )
        return nuevo, {
            "resultado": "aprobada",
            "afirmaciones": len(informe.verificaciones),
            "descendido": False,
            **meta_origen,
        }

    def _consulta_comprobada(self, ctx, respuesta, informe):
        if (ctx.nivel_divulgacion < 2
                or (ctx.continuidad or {}).get('acto') != 'consultar'
                or ctx.intencion not in ('consulta_conceptual', 'solicitud_ejemplo', 'explicacion_directa')):
            return None
        validas = {v.bloque for v in informe.verificaciones if v.aprobada}
        afirmaciones = tuple(a for a in respuesta.afirmaciones if a.identificador in validas)
        if not afirmaciones:
            recuperada = RespuestaGenerada(
                narracion=('No se mostró la tabla porque las fórmulas propuestas no superaron la '
                           'comprobación matemática. Conservé la consulta; podemos revisar una regla '
                           'concreta y su ejemplo, empezando por potencia, producto, cociente o cadena.'),
                nivel_divulgacion=1,
            )
            return self._descender(ctx, recuperada, informe), {
                'resultado': 'consulta sin fórmulas comprobadas', 'descendido': True,
                'afirmaciones': 0, 'afirmaciones_retiradas': len(respuesta.afirmaciones),
                'motivo': informe.motivo_de_rechazo,
            }
        recuperada = RespuestaGenerada(
            narracion=('Estas son las fórmulas comprobadas para esta consulta:\n' +
                '\n'.join('{{' + a.identificador + '}}.' for a in afirmaciones) +
                '\nLa lista es parcial: otras fórmulas de la respuesta no superaron la comprobación. '
                'Las reglas se aplican donde las funciones sean diferenciables y las expresiones estén definidas.'),
            afirmaciones=afirmaciones, nivel_divulgacion=2,
        )
        if recuperada.problemas():
            return None
        comprobacion = self._cas.verificar(recuperada.bloques())
        if not comprobacion.aprobada:
            return None
        return replace(ctx, respuesta=recuperada.narracion, respuesta_generada=recuperada,
                       informe=comprobacion, nivel_divulgacion=2), {
            'resultado': 'consulta parcial comprobada', 'descendido': False,
            'afirmaciones': len(afirmaciones),
            'afirmaciones_retiradas': len(respuesta.afirmaciones) - len(afirmaciones),
            'motivo': informe.motivo_de_rechazo,
        }

    def _respaldo(self, ctx: ContextoTurno, respuesta) -> tuple[ContextoTurno, dict] | None:
        if ctx.nivel_divulgacion < CORRECCION or not ctx.expresiones:
            return None

        activo = ctx.ejercicio_activo or {}
        del_motor = RespuestaGenerada.desde_precomputo(
            ctx.precomputo, ctx.expresiones[0], activo.get("variable", "x"), activo.get("orden", 1),
        )

        if del_motor is None or del_motor.problemas():
            return None

        informe = self._cas.verificar(del_motor.bloques())
        if not informe.aprobada:

            return None

        return replace(
            ctx,
            respuesta=del_motor.narracion,
            respuesta_generada=del_motor,
            informe=informe,
            nivel_divulgacion=del_motor.nivel_divulgacion,
        ), {
            "resultado": "respaldo determinista (D-21)",
            "motivo": "el generador no cumplió el nivel 3 y respondió el motor",
            "afirmaciones": len(informe.verificaciones),
            "descendido": False,

            "respaldo_determinista": True,
        }

    def _sin_afirmaciones(
        self, ctx: ContextoTurno, respuesta, informe, meta_origen: dict
    ) -> tuple[ContextoTurno, dict]:

        respaldo = self._respaldo(ctx, respuesta)
        if respaldo is not None:
            return respaldo

        nivel_pedido = ctx.nivel_divulgacion
        if nivel_pedido <= 1:
            return replace(
                ctx,
                respuesta=respuesta.narracion,
                respuesta_generada=respuesta,
                informe=informe,
                nivel_divulgacion=nivel_pedido,
            ), {
                "resultado": "sondeo sin afirmaciones (ADR-014 C4)",
                "afirmaciones": 0,
                "descendido": False,
                **meta_origen,
            }

        return self._descender(ctx, respuesta.podada(), informe), {
            "resultado": "nivel pedido sin afirmaciones",
            "motivo": f"se pidió nivel {nivel_pedido} y no se declaró ninguna afirmación",
            "afirmaciones": 0,
            "descendido": True,
            **meta_origen,
        }

    @staticmethod
    def _del_turno(ctx: ContextoTurno) -> tuple[RespuestaGenerada | None, dict]:
        generacion = ctx.generacion
        if generacion is None or generacion.estructura is None:
            return None, {"origen": "el generador no entregó estructura (ADR-014 §5.3)"}
        try:
            return RespuestaGenerada.desde_objeto(generacion.estructura), {
                "origen": "estructura del generador"
            }
        except RespuestaMalformada as e:
            return None, {"origen": "estructura malformada (ADR-014 C3)", "motivo": str(e)}

    @staticmethod
    def _descender(
        ctx: ContextoTurno,
        podada: RespuestaGenerada,
        informe: InformeVerificacion | None = None,
    ) -> ContextoTurno:

        return replace(
            ctx,
            respuesta=podada.narracion,
            respuesta_generada=podada,
            informe=informe,
            nivel_divulgacion=1,
        )
