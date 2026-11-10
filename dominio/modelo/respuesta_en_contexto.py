"""Separar una entrega de sus muletillas sin reinterpretar el enunciado activo."""
import re

from dominio.modelo.lectura_oral import LecturaIncierta, expresion_oral
from dominio.modelo.referencias_matematicas import formula_acotada

_ENTREGA = re.compile(r'\b(?:me\s+(?:dio|da|qued[oó]|sale)|derivo\s+como|(?:yo\s+digo\s+que\s+)?es|o\s+sea)\s+', re.I)
_FRACCIONES = {'medio': 2, 'medios': 2, 'tercio': 3, 'tercios': 3,
               'cuarto': 4, 'cuartos': 4, 'quinto': 5, 'quintos': 5,
               'sexto': 6, 'sextos': 6, 'séptimo': 7, 'séptimos': 7,
               'octavo': 8, 'octavos': 8, 'noveno': 9, 'novenos': 9,
               'décimo': 10, 'décimos': 10}


def leer_propuesta(texto, variable='x'):
    s = texto.strip().rstrip('?.! ')
    s = re.split(r'[;!?¿]|\.(?=\s|$)|,\s*(?=[a-záéíóúñ])|\s+(?:porque|aunque|como\s+la|qué\b|que\s+bobada)\b', s, maxsplit=1, flags=re.I)[0].strip().rstrip(', ')
    s = re.sub(r'\ba\s+la\s+(\d+|[xteu])\b', r'^\1', s, flags=re.I)
    s = re.sub(r'\b(al\s+cuadrado|al\s+cubo)\b', lambda m: '^2' if 'cuadrado' in m[0] else '^3', s, flags=re.I)
    s = re.sub(r'\b(\d+)\s+(' + '|'.join(_FRACCIONES) + r')\b',
               lambda m: f'{m[1]}/{_FRACCIONES[m[2].lower()]}', s, flags=re.I)
    if s.lower() == 'no existe':
        return 'no existe'
    if (directa := formula_acotada(s, variable)):
        return directa
    try:
        return formula_acotada(expresion_oral(s, composicion_contextual=True), variable)
    except LecturaIncierta:
        return ''


def respuesta_en_contexto(estado, mensaje):
    if not estado.get('activa') or re.search(r'\b(?:nuevo\s+ejercicio|otra\s+funci[oó]n|cambia|corrijo)\b', mensaje, re.I):
        return False
    from dominio.modelo.pasos_logaritmicos import leer_paso_logaritmico

    if _seleccion_de_metodo(estado, mensaje) or leer_paso_logaritmico(estado, mensaje):
        return True
    if _igualdad_escrita(estado, mensaje) or _resultado_rotulado(estado, mensaje):
        return True
    if re.search(r'\bno\s+entiendo\s+si\b.*\b(?:cubre|solo|s[oó]lo)\b', mensaje, re.I):
        estado.update(acto='continuar', aclaracion='Antes de derivar, confirma la agrupación con paréntesis: ¿la división abarca todo el producto o solamente un factor?')
        return True
    if re.search(r'\bno\s+s[eé]\s+si\b', mensaje, re.I):
        estado.update(acto='iniciar', aclaracion='')
        return True
    if _entrega_anunciada(estado, mensaje):
        return True
    if ':' in mensaje and re.search(r'\bderivada\b', mensaje, re.I) and (propuesta := leer_propuesta(mensaje.split(':', 1)[1])):
        estado.update(acto='responder', propuesta=propuesta, aclaracion='', alcance='final')
        return True
    if re.search(r'=|\b(?:calcula|eval[uú]a|deriva|derivar)\b', mensaje, re.I):
        return False
    if re.search(r'\b(?:no\s+s[eé]|no\s+entiendo|me\s+qued[eé]\s+trabado|ya\s+me\s+enred[eé]|ay[uú]d\w*|me\s+ayuda|c[oó]mo\s+(?:lo|es\s+que|se))\b', mensaje, re.I):
        estado.update(acto='iniciar', aclaracion='')
        return True
    return False


def _seleccion_de_metodo(estado, mensaje):
    if re.search(r'\b(?:le\s+saco|tom[oa]|aplic[oa])\s+(?:el\s+)?(?:ln|logaritmo)\s+(?:a\s+)?todo', mensaje, re.I):
        estado.update(acto='dialogar', propuesta='', aclaracion='', metodo='logaritmico')
        return True
    return False


def _igualdad_escrita(estado, mensaje):
    igualdad = re.search(r'\b(?:queda|obtengo)\s+([^=;!?]+)\s*=\s*(.+)', mensaje, re.I)
    if igualdad:
        actual = next((t for t in estado['tareas'] if t['id'] == estado['activa']), {})
        variable = actual.get('ejercicio', {}).get('variable', 'x')
        izquierda, derecha = leer_propuesta(igualdad[1], variable), leer_propuesta(igualdad[2], variable)
        if izquierda and derecha:
            estado.update(acto='paso_usuario', propuesta=derecha, alcance='parcial', aclaracion='',
                          paso_usuario=dict(transformacion='igualdad', izquierda=izquierda, tarea_id=estado['activa']))
            return True
    return False


def _resultado_rotulado(estado, mensaje):
    final = re.search(r"\b([a-zA-Z])\s*(['’′]+)\s*\(([^()]+)\)\s*=\s*(.+)", mensaje)
    actual = next((t for t in estado['tareas'] if t['id'] == estado['activa']), {})
    variable = actual.get('ejercicio', {}).get('variable', 'x')
    if (final and (propuesta := leer_propuesta(final[4], variable))
            and final[1] == actual.get('nombre') and len(final[2]) == actual['ejercicio'].get('orden', 1)
            and final[3].strip() == actual['ejercicio'].get('variable', 'x')):
        estado.update(acto='responder', propuesta=propuesta, aclaracion='', alcance='final')
        return True
    return False


def consulta_sin_entrega(mensaje):
    consulta = re.search(r'\b(?:por\s+qu[eé]|qu[eé]\s+significa|c[oó]mo\s+se\s+explica)\b', mensaje, re.I)
    entrega = re.search(r'\b(?:me\s+(?:dio|da|sale|qued[oó])|obtengo|mi\s+(?:respuesta|resultado|derivada)|yo\s+(?:digo|creo))\b', mensaje, re.I)
    return bool(consulta and not entrega)


def _entrega_anunciada(estado, mensaje):
    if consulta_sin_entrega(mensaje):
        return False
    # Una entrega anunciada es una propuesta, incluso si repite el enunciado.
    entregas = list(_ENTREGA.finditer(mensaje))
    if entregas:
        for entrega in reversed(entregas):
            if re.search(r'\b(?:exponente|variable|regla|factor)\s+(?:tambi[eé]n\s+)?$', mensaje[:entrega.start()], re.I):
                continue
            if re.search(r'\bno\s*$', mensaje[:entrega.start()], re.I):
                continue
            propuesta = leer_propuesta(mensaje[entrega.end():], (next(
                (t['ejercicio'] for t in estado['tareas'] if t['id'] == estado['activa']), {})).get('variable', 'x'))
            if propuesta:
                estado.update(acto='responder', propuesta=propuesta, aclaracion='')
                if re.search(r'\bderivada\s+(?:de|del)\b|\bresultado\s+final\b|\bel\s+\d+\b', mensaje, re.I):
                    estado['alcance'] = 'final'
                return True
    return False
