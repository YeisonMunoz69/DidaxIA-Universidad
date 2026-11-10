from dataclasses import replace

from dominio.filtros.verificacion import FiltroVerificacion


class FiltroVerificacionRetroalimentacion(FiltroVerificacion):
    def _procesar(self, ctx):
        if ctx.retroalimentacion_del_intento is not None and self._respuesta is None:
            return self._retroalimentar(ctx)
        return super()._procesar(ctx)

    def _retroalimentar(self, ctx):
        base = ctx.retroalimentacion_del_intento
        candidata, origen = self._del_turno(ctx)
        cumple = (
            candidata is not None and not candidata.problemas()
            and candidata.nivel_divulgacion == 2
            and candidata.narracion.startswith(base.narracion)
            and not any(signo in candidata.narracion for signo in ("?", "¿"))
            and all(a in candidata.afirmaciones for a in base.afirmaciones)
            and all(c in candidata.citadas for c in base.citadas)
        )
        informe = self._cas.verificar(candidata.bloques()) if cumple else None
        usa_generador = bool(informe and informe.aprobada)
        elegida = candidata if usa_generador else base
        informe = informe if usa_generador else self._cas.verificar(base.bloques())
        if elegida.problemas() or not informe.aprobada:
            return self._descender(ctx, elegida.podada(), informe), {
                "resultado": "referencia de retroalimentación no verificable", "descendido": True,
            }
        return replace(ctx, respuesta=elegida.narracion, respuesta_generada=elegida,
                       informe=informe, nivel_divulgacion=2), {
            "resultado": ("retroalimentación de paso comprobado" if ctx.paso_pendiente
                          else "retroalimentación de propuesta refutada comprobada"),
            "descendido": False, "afirmaciones": len(informe.verificaciones),
            "explicacion_del_generador": usa_generador, "respaldo_determinista": not usa_generador,
            "correccion_del_resultado_entregada": (ctx.paso_pendiente.get("veredicto") == "invalida"
                                                   if ctx.paso_pendiente else True),
            "alcance": "paso_preguntado" if ctx.paso_pendiente else "resultado_final",
            "motivo": "ampliación compatible verificada" if usa_generador else "el generador no entregó una ampliación compatible; se emite la base comprobada",
            **origen,
        }
