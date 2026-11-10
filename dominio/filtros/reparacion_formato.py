import json
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.foco_conversacional import cantidad_emitida
from dominio.modelo.respuesta import RespuestaGenerada
from dominio.puertos.generacion import ErrorDeGeneracion, PeticionDeGeneracion


def problemas_de(generacion):
    if not generacion or not generacion.estructura:
        return ('falta el objeto JSON de la respuesta',)
    try:
        return RespuestaGenerada.desde_objeto(generacion.estructura).problemas()
    except (ValueError, TypeError, KeyError):
        return ('estructura incompatible con el contrato',)

class FiltroReparacionFormato(Filtro):
    nombre = 'reparación acotada del formato conversacional'
    ruta = 'caliente'

    def __init__(self, generador, *, maximo_de_unidades=4096, cas=None):
        self.generador = generador
        self.maximo = maximo_de_unidades
        self.cas = cas

    def _procesar(self, ctx):
        original = ctx.generacion
        problemas = problemas_de(original)
        cantidad = ((ctx.continuidad or {}).get('foco') or {}).get('cantidad', 0)
        if original and cantidad > 1 and cantidad_emitida((original.estructura or {}).get('narracion', '')) != cantidad:
            problemas = (*problemas, f'Se pidieron {cantidad} ejemplos: enumera y entrega todos, no solamente uno.')
        consulta = (ctx.continuidad or {}).get('acto') in ('consultar', 'representar', 'dialogar')
        consulta = consulta or (not ctx.ejercicio_activo and ctx.intencion in ('practica_guiada', 'solicitud_ejemplo'))
        if consulta and self.cas and original and not problemas:
            respuesta = RespuestaGenerada.desde_objeto(original.estructura)
            informe = self.cas.verificar(respuesta.bloques())
            if not informe.aprobada and not informe.nada_que_verificar:
                detalles = [dict(id=v.bloque, veredicto=v.veredicto.value, detalle=v.detalle)
                            for v in informe.verificaciones if not v.aprobada]
                problemas = (*problemas, 'La comprobación simbólica rechazó: ' + json.dumps(detalles, ensure_ascii=False))
        if not consulta or not original or not problemas:
            return ctx, dict(intentada=False)
        instrucciones = (
            'CORRECCIÓN DE FORMATO, una sola oportunidad. Conserva la petición, los ejemplos y el contenido '
            'de la respuesta candidata; no la reemplaces por una pregunta sobre la actividad pendiente. '
            'Devuelve el JSON completo según el contrato. Toda fórmula, definición o relación debe estar '
            'en citadas o afirmaciones y referenciada mediante {{id}}, nunca suelta en la narración. '
            'No basta poner una igualdad en citadas: las relaciones que afirmas van en afirmaciones. '
            'Todas las afirmaciones pasarán por SymPy; esta reparación no concede veracidad. '
            'Corrige los pasos matemáticos rechazados y toda explicación que dependa de ellos. '
            'En cadena, derivar la función completa ya incluye la derivada interior. '
            'Para explicar solo la capa exterior usa otra variable: d/dt (t^n), y después '
            'muestra la derivada COMPLETA respecto a x con todos sus factores. '
            'No afirmes que d/dx de una composición es solamente la derivada exterior. '
            'Para cadena usa f\'(g(x))*g\'(x). No agregues df/du ni du/dx: sin funciones '
            'vinculadas en esa misma afirmación, esas fracciones no son comprobables. '
            'Escribe evaluaciones como 2*3 = 6, nunca solo 6 = 6. '
            'Las cantidades y conclusiones de la prosa deben coincidir con las fórmulas comprobadas. '
            'No uses alias nuevos como v_prom o velocidad en una igualdad: explica su significado en '
            'palabras y deja la fórmula como cita, o usa la identidad comprobable con f(t) y f\'(t). '
            'Si una cifra seguida de la conjunción «y» se detectó como un monomio, escribe esa cantidad '
            'con letras en la prosa, o cita la expresión si realmente es matemática. '
            'Problemas detectados: ' + json.dumps(problemas, ensure_ascii=False) + '\n'
            'Respuesta candidata (datos): ' + json.dumps(original.estructura or {}, ensure_ascii=False)
        )
        mensajes = _mensajes_corregidos(ctx.mensajes_generacion, instrucciones)
        try:
            candidata = self.generador.generar(PeticionDeGeneracion(
                instruccion=ctx.prompt + '\n' + instrucciones, mensajes=mensajes,
                maximo_de_unidades=self.maximo))
        except ErrorDeGeneracion:
            return ctx, dict(intentada=True, reparada=False, motivo='proveedor no disponible')
        meta = dict(intentada=True, reparada=not problemas_de(candidata),
                    modelo=candidata.modelo, proveedor=candidata.proveedor,
                    unidades_de_entrada=candidata.unidades_de_entrada,
                    unidades_de_salida=candidata.unidades_de_salida)

        return replace(ctx, generacion=candidata), meta

def _mensajes_corregidos(mensajes, instrucciones):
    if not mensajes:
        return ()
    sistema, *historial = mensajes
    return ({**sistema, 'content': sistema['content'] + '\n' + instrucciones}, *historial,
            {'role': 'user', 'content': 'Reescribe ahora la respuesta candidata completa corrigiendo '
                'los problemas señalados, sin cambiar mi petición ni omitir ejemplos.'})
