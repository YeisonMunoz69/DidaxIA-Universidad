import re

from dominio.modelo.notacion_entrada import normalizar_escritura_matematica


def leer_paso_logaritmico(estado, mensaje):
    actual = next((t for t in estado['tareas'] if t['id'] == estado['activa']), {})
    nombre = actual.get('nombre')
    if not nombre or actual.get('ejercicio', {}).get('tipo') != 'derivada':
        return False
    n = re.escape(nombre)
    variable = actual['ejercicio'].get('variable', 'x')
    argumento = re.escape(variable)
    s = normalizar_escritura_matematica(mensaje).replace('’', "'").replace('′', "'")
    if _ultimo_termino(estado, s, variable):
        return True
    log = rf'\bln\s*(?:\(\s*{n}(?:\({argumento}\))?\s*\)|{n}(?:\({argumento}\))?)'
    cociente = rf"\b{n}'(?:\({argumento}\))?\s*/\s*{n}(?:\({argumento}\))?"
    if re.search(rf'{log}|{cociente}', s):
        from dominio.modelo.respuesta_en_contexto import leer_propuesta

        tipo, texto = '', ''
        if (m := re.search(rf'{cociente}\s*=\s*(.+)', s)) or (m := re.search(rf'derivada\s+de\s+{log}\s+(?:es|da)\s+(.+)', s, re.I)):
            tipo, texto = 'derivada_log', m[1]
        elif m := re.search(rf'{log}\s*=\s*(.+)', s):
            tipo, texto = 'log', re.split(r'(?:eso\s+queda|queda)\s+', m[1], flags=re.I)[-1]
        if tipo and texto:

            texto = re.sub(rf'\b{n}(?:\({argumento}\))?(?![a-zA-Z])', '(' + actual['ejercicio']['expresion'] + ')', texto)
            partes = [leer_propuesta(p, variable) for p in texto.split('=')]
            if 1 <= len(partes) <= 8 and all(partes):
                propuesta = partes[-1]
                estado.update(acto='paso_usuario', propuesta=propuesta, aclaracion='', alcance='parcial',
                              paso_usuario=dict(transformacion=tipo, tarea_id=estado['activa'], transiciones=partes[:-1]))
                return True

        estado.update(acto='dialogar', propuesta='', aclaracion='')
        return True
    return False

def _ultimo_termino(estado, mensaje, variable):
    from dominio.modelo.respuesta_en_contexto import leer_propuesta

    marca = re.search(r'\bel\s+[uú]ltimo(?:\s+t[eé]rmino)?\s*(?:[.,…:]+|(?:me\s+)?da\s+|queda\s+|es\s+)(.+)',
                      mensaje, re.I)
    if not marca or not (propuesta := leer_propuesta(marca[1], variable)):
        return False
    fuente = next((e['propuesta'] for e in reversed(estado['evidencias'])
                   if e.get('tarea') == estado['activa'] and
                   (e.get('paso') or {}).get('transformacion') == 'log' and
                   (e.get('paso') or {}).get('veredicto') == 'valida'), '')
    if not fuente:
        return False
    estado.update(acto='paso_usuario', propuesta=propuesta, aclaracion='', alcance='parcial',
                  paso_usuario=dict(transformacion=dict(tipo='derivada_termino_log', fuente=fuente),
                                    tarea_id=estado['activa']))
    return True
