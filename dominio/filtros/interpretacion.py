from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.factores_conductuales import RUBRICA, VERSION
from dominio.pedagogia.confirmacion import base_de_ejercicio
from dominio.pedagogia.intenciones import AMBIGUA, CATALOGO, INTENTO_RESOLUCION, Intencion
from dominio.puertos.interpretacion import PuertoInterpretacion


class FiltroInterpretacion(Filtro):
    nombre = "interpretación semántica experimental"
    ruta = "caliente"

    def __init__(self, interprete: PuertoInterpretacion, *, observar: bool = False):
        self.interprete = interprete
        self.observar = observar

    def _procesar(self, ctx):
        original = ctx.intencion_detalle or Intencion()
        meta = {"version": "interpretacion.prototipo.v3", "regla": original.como_dict(),
                "aplicada": False, "intencion_efectiva": original.clase, "cambios": []}

        conservar_intencion = (original.confirma_ayuda or original.sin_adaptacion
                               or original.reactiva_adaptacion or original.es_cortesia)
        habilitar_factores = (bool(ctx.identificador_sujeto)
                              and ctx.contexto_de_uso == "aprendizaje_estudiante")
        if conservar_intencion and not (habilitar_factores and getattr(self.interprete, "factores_conductuales", False)):
            return ctx, {**meta, "omitida": "preferencia o confirmación explícita"}
        entrada = {
            "mensaje": ctx.texto_estudiante[:4000],
            "ejercicio_activo": ctx.ejercicio_activo,
            "historial": [
                {"estudiante": t.get("estudiante", "")[:1500], "tutor": t.get("tutor", "")[:2500]}
                for t in ctx.historial_reciente[-3:]
            ],
            "regla": original.como_dict(),
            "habilitar_factores": habilitar_factores,
            "solo_factores": conservar_intencion,
        }
        if ctx.continuidad is not None:
            from dominio.modelo.continuidad import para_interpretacion
            entrada["estado_operativo"] = para_interpretacion(ctx.continuidad)
        if ctx.contexto_conversacional is not None:
            entrada["contexto_conversacional"] = ctx.contexto_conversacional
            entrada['evidencia_matematica'] = _comprobaciones_anteriores(ctx)
        try:
            lectura = self.interprete.interpretar(entrada)
            if lectura.clase not in CATALOGO or not lectura.evidencia or lectura.evidencia not in entrada["mensaje"]:
                raise ValueError("lectura sin evidencia del turno actual")
        except Exception as exc:
            return ctx, {**meta, "fallback": type(exc).__name__}
        meta["lectura"] = {
            "clase": lectura.clase, "evidencia": lectura.evidencia,
            "motivo": lectura.motivo, "modelo": lectura.modelo,
            "estrategia_solicitada": lectura.estrategia_solicitada,
            "pide_menos_preguntas": lectura.pide_menos_preguntas,
            "propone_solucion": lectura.propone_solucion,
            "necesidad": lectura.necesidad,
        }
        ctx = _anotar_lectura(ctx, lectura, meta, entrada)
        if conservar_intencion:
            return ctx, {**meta, "no_aplicada_por": "preferencia o confirmación explícita"}
        if self.observar or lectura.clase == AMBIGUA:
            return ctx, {**meta, "no_aplicada_por": "solo observación" if self.observar else "lectura ambigua"}

        from dominio.filtros.intencion import extraer_ejercicio_explicito
        from dominio.filtros.intento import anuncia_resultado
        from dominio.modelo.respuesta_en_contexto import consulta_sin_entrega

        preservar_propuesta = original.propone_solucion and not consulta_sin_entrega(ctx.texto_estudiante)
        clase = INTENTO_RESOLUCION if preservar_propuesta else lectura.clase
        es_enunciado = (extraer_ejercicio_explicito(ctx.texto_estudiante) is not None
                        and not anuncia_resultado(ctx.texto_estudiante))
        if es_enunciado and clase == INTENTO_RESOLUCION:
            clase = "practica_guiada"
        nueva = replace(
            original, clase=clase, origen="semantica_experimental",
            motivo=lectura.motivo,
            estrategia_solicitada=lectura.estrategia_solicitada or original.estrategia_solicitada,
            pide_menos_preguntas=original.pide_menos_preguntas or lectura.pide_menos_preguntas,
            propone_solucion=(preservar_propuesta or lectura.propone_solucion) and not es_enunciado,
        )
        cambios = [
            {"campo": campo, "antes": getattr(original, campo), "despues": getattr(nueva, campo)}
            for campo in ("clase", "estrategia_solicitada", "pide_menos_preguntas", "propone_solucion")
            if getattr(original, campo) != getattr(nueva, campo)
        ]
        necesidad = "primer_paso" if es_enunciado and lectura.necesidad == "revisar_resultado" else lectura.necesidad
        if necesidad and necesidad != ctx.necesidad_pedagogica:
            cambios.append({"campo": "necesidad_pedagogica", "antes": ctx.necesidad_pedagogica,
                            "despues": necesidad})

        return replace(ctx, intencion=nueva.clase, intencion_origen=nueva.origen,
                       intencion_detalle=nueva, necesidad_pedagogica=necesidad), {
            **meta, "aplicada": True, "intencion_efectiva": nueva.clase, "cambios": cambios,
            "propuesta_preservada": original.propone_solucion and not lectura.propone_solucion,
        }

def _comprobaciones_anteriores(ctx):
    contexto = ctx.contexto_conversacional or {}
    base = base_de_ejercicio(ctx.ejercicio_activo) if ctx.ejercicio_activo else ''
    return [dict(turno=t['numero'], intento=dict(
        base=base, propuesta=t.get('propuesta', ''), veredicto=t['veredicto_del_intento']),
        correccion_entregada=t.get('correccion_del_resultado_entregada') is True)
        for t in contexto.get('comprobaciones_anteriores', [])
        if base and t.get('veredicto_del_intento') in ('valida', 'invalida')][-4:]

def _anotar_lectura(ctx, lectura, meta, entrada):
    if ctx.continuidad is not None:
        ctx = replace(ctx, actos_conversacionales=lectura.actos)
        meta["actos"] = [{"tipo": a.get("tipo"), "tarea_id": a.get("tarea_id", "")} for a in lectura.actos]
    if entrada["habilitar_factores"] and (lectura.factores or lectura.error_factores):
        meta["analisis_conductual"] = {
            'revision_prompt': RUBRICA['revision_prompt'],
            "version": VERSION, "modelo": lectura.modelo,
            "observaciones": [o.como_dict() for o in lectura.factores],
            "error": lectura.error_factores,
        }
    return ctx
