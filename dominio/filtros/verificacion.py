"""
verificacion.py — Filtro 9 de la cadena
=======================================

`ADR-001` §6.3 lo declara **ruta caliente** con una nota que no admite lectura
ambigua: *«no puede ser fría: ninguna salida matemática se emite sin verificar»*.

Qué hace, en orden
------------------
1. Comprueba que la respuesta **cumpla el contrato** de `ADR-014`. Si no lo
   cumple, desciende sin llegar a invocar el motor: no hay nada fiable que
   verificar.
2. Verifica **todas** las afirmaciones declaradas, por el puerto simbólico.
3. Si alguna no es válida, o si no se pudo verificar, **desciende al nivel 1**.

La regla que hace seguro este filtro
------------------------------------
> **El descenso es el modo por defecto, y aprobar es la excepción que hay que
> ganar.**

Es la inversión que `ADR-008` V1 introdujo. La iteración 0 hacía lo contrario:
aprobaba cuando ningún patrón casaba, de modo que **no saber** era indistinguible
de **estar bien**.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import CORRECCION
from dominio.filtros.base import Filtro
from dominio.modelo.matematica import InformeVerificacion
from dominio.modelo.respuesta import RespuestaGenerada, RespuestaMalformada
from dominio.modelo.turno import ContextoTurno


class FiltroVerificacion(Filtro):
    """Arbitra la corrección matemática de la respuesta antes de emitirla."""

    nombre = "verificación simbólica"
    ruta = "caliente"

    def __init__(self, puerto_simbolico, respuesta: RespuestaGenerada | None = None):
        """`respuesta` es una costura de prueba, no la vía normal.

        En producción la respuesta llega **del turno**: el filtro 8 la deja en
        `ctx.generacion.estructura` y aquí se construye con `desde_objeto()`.
        Inyectarla por constructor sirve para probar este filtro sin proveedor,
        y cuando se pasa **manda sobre lo que traiga el contexto**, que es lo
        que permite fijar el caso bajo prueba.

        ⚠️ Hasta `PM-B17` —2026-08-10— esta era la ÚNICA vía, así que en
        producción nunca había nada que verificar y **todo turno terminaba en
        degradación**, aunque el modelo hubiera respondido bien. Se midió contra
        DeepSeek antes de arreglarlo: la cadena entera corría, la respuesta era
        buena, y el filtro la descartaba sin mirarla.
        """
        self._cas = puerto_simbolico
        self._respuesta = respuesta

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:  # noqa: C901 — puertas de contrato, CAS y arbitraje en orden explícito
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
            # Sin respuesta que verificar el turno no puede continuar: emitir
            # algo no verificado sería exactamente lo que ADR-008 impide.
            return replace(ctx, nivel_divulgacion=1), {
                "resultado": "sin respuesta que verificar",
                "descendido": True,
                **meta_origen,
            }

        # ── 1 · el contrato, antes que el motor ──────────────────────────────
        problemas = respuesta.problemas()
        if problemas:
            podada = respuesta.podada()
            return self._descender(ctx, podada), {
                "resultado": "contrato incumplido",
                "motivos": problemas,
                "descendido": True,
                **meta_origen,
            }

        # ── 2 · barrido exhaustivo ───────────────────────────────────────────
        informe = self._cas.verificar(respuesta.bloques())

        # ── 2.bis · no había nada que verificar · `D-20`, 2026-08-13 ─────────
        if informe.nada_que_verificar:
            return self._sin_afirmaciones(ctx, respuesta, informe, meta_origen)

        # ── 3 · descenso si algo no se sostiene ──────────────────────────────
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
        """Una tabla parcial debe mostrar lo comprobado, sin prometer lo retirado.

        Sólo consultas de referencia: nunca califica parcialmente una entrega
        del estudiante ni conserva la explicación de una regla rechazada.
        """
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
        """`PM-B31` · `D-21`. El motor responde cuando el generador no cumple.

        Entra **solo en nivel 3**, que es donde el sistema ha prometido la
        corrección verificada y donde caer a un sondeo deja a quien lleva cinco
        intentos exactamente igual que a quien acaba de llegar. En nivel 2 no
        entra a propósito: una pista dirigida que se convierte en el desarrollo
        entero se salta un escalón de la escala de `RF-GEN-05`.

        **Y el respaldo se VERIFICA como cualquier otra respuesta.** No es una
        excepción al contrato ni un sello regalado: se construye, se pasa por el
        mismo motor y solo se emite si aprueba. Viene del CAS, así que aprueba
        por construcción — pero si algún día no lo hiciera, desciende como todo
        lo demás. Un camino que se saltara la verificación sería exactamente lo
        que `ADR-008` V1 impide.

        `None` cuando no procede o cuando no hay con qué, y entonces el turno
        sigue por el camino de siempre.
        """
        # ⚠️ **El nivel del ARBITRAJE, no el que el generador declaró.** Lo
        # encontró la prueba de integración de este respaldo: con el arbitraje
        # en 1 y un generador que se ponía `"nivel": 3` en su propio JSON, el
        # respaldo entraba y el estudiante recibía el desarrollo entero **sin
        # haberlo ganado**. `ADR-014` §5.1 lo dice con todas las letras —el
        # nivel *«lo fijó el arbitraje antes de generar; el generador lo recibe,
        # no lo decide»*— y mirar `respuesta.nivel_divulgacion` aquí era
        # dejarle decidir por la puerta de atrás.
        if ctx.nivel_divulgacion < CORRECCION or not ctx.expresiones:
            return None

        activo = ctx.ejercicio_activo or {}
        del_motor = RespuestaGenerada.desde_precomputo(
            ctx.precomputo, ctx.expresiones[0], activo.get("variable", "x"), activo.get("orden", 1),
        )
        # 🐛 El contrato ANTES que el motor, en el mismo orden que el camino
        # normal — y no es teórico: la primera versión de `desde_precomputo`
        # metía LaTeX en la narración y `C1` la invalidaba. Comprobar solo el
        # motor la habría emitido igual.
        if del_motor is None or del_motor.problemas():
            return None

        informe = self._cas.verificar(del_motor.bloques())
        if not informe.aprobada:
            # El CAS contradiciéndose a sí mismo no se emite «porque viene del
            # motor»: se declara y se sigue al descenso normal.
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
            # `D-21` pide contarlo: si entra en la mitad de los turnos de nivel
            # 3, el tutor conversacional no está cumpliendo su parte, y eso es
            # un resultado de la tesis y no un detalle de implementación.
            "respaldo_determinista": True,
        }

    def _sin_afirmaciones(
        self, ctx: ContextoTurno, respuesta, informe, meta_origen: dict
    ) -> tuple[ContextoTurno, dict]:
        """Qué hacer cuando la respuesta no declaró ninguna afirmación.

        **Y son dos casos distintos, no uno**, que es lo que este método existe
        para separar:

        - **En nivel 1 es CORRECTO.** `ADR-014` C4 lo dice con todas las
          letras: *«una pregunta socrática no contiene nada que verificar»*. El
          turno pasa entero, sin descender, y la traza lo dice así. Hasta el
          2026-08-13 aquí se marcaba «verificación no superada» y se descendía
          a un nivel que ya era 1 — una etiqueta equivocada en **todos** los
          turnos del sistema, y el eslabón que cerraba el lazo de `PM-V15`.
        - **En nivel 2 o 3 NO lo es.** Al generador se le pidió nombrar la
          regla o desarrollar el paso, y no declaró nada que comprobar. Eso
          sigue siendo un descenso —el estudiante no puede recibir «desarrollo»
          sin desarrollo— pero con **su propio motivo**, que es lo que permite
          medir con qué frecuencia el generador incumple el nivel que se le
          pidió. Antes se confundía con una verificación fallida y esa cifra no
          se podía sacar de ningún sitio.
        """
        respaldo = self._respaldo(ctx, respuesta)
        if respaldo is not None:
            return respaldo

        # El nivel que se PIDIÓ es el del arbitraje, por el mismo motivo que en
        # `_respaldo`: si se leyera el que el generador declaró, bastaría con
        # que se pusiera `"nivel": 1` para que no declarar nada dejara de ser
        # un incumplimiento.
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
        """La respuesta que el filtro 8 dejó, construida según `ADR-014`.

        Tres desenlaces, y cada uno deja dicho cuál fue:

        - **No hubo generación**, o el adaptador no obtuvo estructura. El turno
          desciende sin nada que verificar. Es el caso de un proveedor que
          ignoró el formato, y `R-21` anticipa que ocurrirá a veces.
        - **El objeto está malformado.** `C3` es explícito: *no se reintenta en
          silencio*; se registra y se desciende al nivel 1. Reintentar aquí
          escondería latencia que `RNF-EFI-01` presupuesta, y callarlo sería la
          degradación silenciosa que `ADR-007` E6 prohíbe.
        - **El objeto está bien.** Sigue el camino normal y se verifica.

        El motivo del fallo va a la traza y **no al estudiante**: nombra el
        formato interno del generador, que es de la clase de dato que
        `08-Contrato-del-Turno.md` §9 no deja cruzar.
        """
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
        """Desciende al nivel 1 conservando la traza de por qué se descendió."""
        return replace(
            ctx,
            respuesta=podada.narracion,
            respuesta_generada=podada,
            informe=informe,
            nivel_divulgacion=1,
        )
