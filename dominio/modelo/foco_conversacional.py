"""Petición actual, actividad y materiales son referentes diferentes del hilo.

La lectura semántica propone el foco; el servidor acepta sólo referencias a
materiales realmente emitidos. Cambiar de foco nunca acredita una tarea.
"""
import hashlib
import re
from copy import deepcopy
from dataclasses import replace

from dominio.pedagogia.intenciones import Intencion

CONSULTAS = {'consulta_conceptual', 'explicacion_directa', 'solicitud_ejemplo',
             'aplicacion_transferencia', 'cambio_estrategia', 'bloqueo_explicito'}
_CANTIDADES = dict(uno=1, un=1, dos=2, tres=3, cuatro=4, cinco=5, seis=6,
                  siete=7, ocho=8, nueve=9, diez=10)


def cantidad_pedida(mensaje):
    cantidad = re.search(r'\b(\d+|' + '|'.join(_CANTIDADES) + r')\s+(?:ejemplos|ejercicios)\b', mensaje, re.I)
    if not cantidad:
        return 0
    texto = cantidad[1].lower()
    valor = int(texto) if texto.isdigit() else _CANTIDADES[texto]
    return valor if 1 <= valor <= 20 else 0


def cantidad_emitida(narracion):
    etiquetas = re.findall(r'(?:^|\s)(?:(?:Ejemplo|Ejercicio)\s+)?(\d+)[.):]\s', narracion.replace('**', ''), re.I)
    return len(set(etiquetas))


def material_solicitado(estado, actos, mensaje):
    materiales = estado.get('materiales', [])
    if cantidad_pedida(mensaje) and re.search(r'\b(?:adicionales|nuevos|complicados|ahora\s+dame)\b', mensaje, re.I):
        return None
    for acto in actos:
        evidencia = acto.get('evidencia', '')
        if acto.get('tipo') == 'consultar' and evidencia and evidencia in mensaje:
            encontrado = next((m for m in materiales if m['id'] == acto.get('material_id')), None)
            if encontrado:
                return encontrado
    # Respaldo para referencias explícitas a la lista recién emitida.
    referencia = re.search(r'\b(?:esos|estos|sus|cada\s+uno|los\s+ejemplos|los\s+ejercicios)\b', mensaje, re.I)
    desarrollo = re.search(r'soluci[oó]n|soluciones|procesos|procedimiento|resu[eé]lv|resolver|desarroll', mensaje, re.I)
    return materiales[-1] if materiales and referencia and desarrollo else None


def enfocar(estado, intencion, actos, mensaje):
    estado = deepcopy(estado)
    intencion = intencion or Intencion()
    material = material_solicitado(estado, actos, mensaje)
    if material:
        intencion = replace(intencion, clase='solicitud_ejemplo', propone_solucion=False)
    if estado.get('activa') and re.fullmatch(r'\s*no\s+s[eé][.!?\s]*', mensaje, re.I):
        intencion = replace(intencion, clase='bloqueo_explicito', propone_solucion=False)
    consulta = intencion.clase in CONSULTAS and (material is not None or estado.get('acto') != 'responder')
    cantidad = cantidad_pedida(mensaje) if intencion.clase == 'solicitud_ejemplo' else 0
    if material and re.search(r'\b(?:cada\s+uno|todos|sus\s+soluciones)\b', mensaje, re.I):
        cantidad = material.get('cantidad', 0)
    estado['foco'] = dict(tipo='consulta' if consulta else 'actividad',
                          clase=intencion.clase, material_id=material['id'] if material else '',
                          cantidad=cantidad)
    if consulta:
        estado.update(acto='representar' if estado.get('acto') == 'representar' else 'consultar', propuesta='', aclaracion='')
    return estado, intencion


def recordar_material(estado, respuesta, mensaje=''):
    """Guardar lo emitido, no ejemplos que el modelo sólo prometió generar."""
    foco = estado.get('foco', {})
    referencia = bool(re.search(r'\b(?:tabla|f[oó]rmulas|reglas)\b', mensaje, re.I)
                      and respuesta and len(respuesta.afirmaciones) >= 2)
    if (foco.get('clase') != 'solicitud_ejemplo' and not referencia) or foco.get('material_id') or not respuesta:
        return
    if len(respuesta.citadas) < 2 and not respuesta.afirmaciones:
        return
    material = dict(id='material-' + str(estado['revision']),
                    tipo='referencia' if referencia else 'ejemplos',
                    narracion=respuesta.narracion[:18000],
                    cantidad=cantidad_emitida(respuesta.narracion),
                    citadas=[dict(id=c.identificador, expresion=c.expresion) for c in respuesta.citadas[:40]],
                    afirmaciones=[dict(id=a.identificador, izquierda=a.izquierda, derecha=a.derecha,
                                       relacion=a.relacion) for a in respuesta.afirmaciones[:40]])
    estado.setdefault('materiales', []).append(material)
    referencias = [m for m in estado['materiales'] if m.get('tipo') == 'referencia'][-1:]
    recientes = [m for m in estado['materiales'] if m not in referencias][-3:]
    estado['materiales'] = [m for m in estado['materiales'] if m in referencias or m in recientes]


def materiales_para_prompt(estado):
    materiales = estado.get('materiales', [])
    referencias = [m for m in materiales if m.get('tipo') == 'referencia'][-1:]
    return deepcopy(referencias + [m for m in materiales[-2:] if m not in referencias])


def recuperar_materiales_emitidos(estado, voces):
    """Compatibilidad con hilos anteriores: solo listas que el tutor ya emitió.

    El historial preserva un referente, nunca acredita la verdad del contenido.
    Las soluciones futuras seguirán pasando por la verificación simbólica.
    """
    if estado.get('materiales'):
        return
    materiales = []
    for voz in voces[-6:]:
        cantidad = cantidad_pedida(voz.get('estudiante', ''))
        narracion = voz.get('tutor', '')
        if cantidad < 2 or cantidad_emitida(narracion) != cantidad or '{{' in narracion:
            continue
        materiales.append(dict(id='material-historico-' + hashlib.sha256(narracion.encode()).hexdigest()[:16],
                               narracion=narracion[:18000], cantidad=cantidad, citadas=[], afirmaciones=[]))
    if materiales:
        estado['materiales'] = materiales[-4:]
