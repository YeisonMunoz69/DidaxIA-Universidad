"""Contrastes matemáticos explícitos que impiden algunos falsos positivos.

No decide todas las concepciones ni usa cantidad de mensajes como evidencia.
Si el referente es ambiguo suspende la detección; no corrige la lectura privada
guardada ni infiere emociones. Los casos no cubiertos conservan la rúbrica.
"""
import re
import unicodedata


def contrastar(mensaje, observacion):
    if observacion.get('estado') != 'detectado':
        return observacion
    texto = ''.join(c for c in unicodedata.normalize('NFD', mensaje.lower()) if not unicodedata.combining(c))
    cita = ''.join(c for c in unicodedata.normalize('NFD', observacion.get('evidencia',mensaje).lower()) if not unicodedata.combining(c))
    # La imposibilidad de dividir por cero es correcta. No implica por sí
    # misma que el límite no exista. No completar esa inferencia ausente.
    division_indefinida = re.search(
        r'\bdivi\w*\s+por\s+(?:0|cero)\s+(?:lo cual\s+|y eso\s+|y\s+)?'
        r'(?:no se puede|no esta definid[oa])\s*[.!]?\s*$', cita)
    otra_afirmacion = re.search(
        r'limite.{0,40}no existe|0/0.{0,30}(?:da|es|=)\s*(?:0|cero)\b|'
        r'divi\w*.{0,30}(?:da|es|=)\s*(?:0|cero)\b|producto de.*derivad', texto)
    if division_indefinida and not otra_afirmacion:
        return {**observacion, 'estado': 'no_detectado', 'oportunidad': True,
                'motivo': 'La división por cero no está definida; el mensaje no afirma que por ello el límite no exista.',
                'contraste_matematico': True}
    # El contraste debe referirse a la proposición citada. Una frase correcta
    # no borra otra relación errónea del mismo mensaje.
    if re.search(r'0/0|divid.*cero|producto de.*derivad|no es (?:cierto|verdad|correcto)|es falso|es mentira', cita):
        return observacion
    estado, motivo, oportunidad = None, None, True
    if re.search(r'(distint[oa]s|diferentes)', cita) and re.search(r'limite (?:bilateral )?no existe', cita):
        explicitos = 'laterales' in texto or ('derecha' in texto and 'izquierda' in texto)
        estado = 'no_detectado' if explicitos else 'no_concluyente'
        motivo = 'Límites laterales distintos impiden el límite bilateral.' if explicitos else 'Falta identificar qué valores son distintos; no se sostiene una relación errónea verificable.'
    if ('metodo' in cita and ('profe' in texto or 'docente' in texto)
            and ('derecha' in cita and 'izquierda' in cita)
            and not re.search(r'unico|siempre|nunca|no existe|igual a|da cero', texto)):
        estado, oportunidad = 'no_detectado', False
        motivo = 'Solicitar un método numérico de clase no afirma por sí mismo una relación conceptual errónea.'
    producto = re.search(r'cercanos a\s*(-?\d+(?:[.,]\d+)?)\s+por\s*(-?\d+(?:[.,]\d+)?)\s+da\s+(negativo|positivo)', cita)
    if producto:
        a, b = (float(producto[i].replace(',', '.')) for i in (1, 2))
        if a != 0 and b != 0 and ((a * b < 0) == (producto[3] == 'negativo')):
            estado = 'no_detectado'
            motivo = 'En un entorno suficientemente pequeño del número no nulo, el signo del producto indicado es correcto.'
    if estado is None:
        return observacion
    return {**observacion, 'estado': estado, 'oportunidad': oportunidad, 'motivo': motivo,
            'contraste_matematico': True}
