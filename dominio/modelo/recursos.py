from __future__ import annotations

import math
import re
from datetime import date
from urllib.parse import urlsplit

from dominio.modelo.imagenes_encuesta import validar_imagenes_encuesta

TIPOS_PREGUNTA = {'texto', 'parrafo', 'unica', 'multiple', 'desplegable', 'escala', 'numero', 'fecha', 'correo'}


class RecursoInvalido(ValueError):
    pass

def texto(valor, limite=5000, obligatorio=False):
    if not isinstance(valor, str) or '\x00' in valor or len(valor) > limite:
        raise RecursoInvalido('El texto no es válido o supera la longitud permitida.')
    if obligatorio and not valor.strip():
        raise RecursoInvalido('Completa los títulos y las preguntas.')
    return valor.strip()

def enlace_seguro(valor):
    if not valor:
        return ''
    valor = texto(valor, 2000)
    url = urlsplit(valor)
    if url.scheme not in {'http', 'https', 'mailto'} or (url.scheme != 'mailto' and not url.netloc):
        raise RecursoInvalido('Los enlaces deben usar http, https o mailto.')
    return valor

def _validar_exclusivas(pregunta):
    if 'exclusivas' not in pregunta:
        return
    opciones = pregunta['exclusivas']
    if pregunta['tipo'] != 'multiple' or not isinstance(opciones, list) or any(not isinstance(o, str) or o not in pregunta['opciones'] for o in opciones):
        raise RecursoInvalido('Las opciones excluyentes deben pertenecer a una pregunta de selección múltiple.')

def validar_recurso(cuerpo, *, publicable=False):
    tipo = cuerpo.get('tipo')
    if not isinstance(tipo, str) or tipo not in {'encuesta', 'diapositivas'}:
        raise RecursoInvalido('Tipo de recurso desconocido.')
    titulo = texto(cuerpo.get('titulo'), 250, publicable)
    descripcion = texto(cuerpo.get('descripcion', ''), 5000)
    contenido = cuerpo.get('contenido')
    if not isinstance(contenido, dict):
        raise RecursoInvalido('Falta el contenido del recurso.')
    if tipo == 'diapositivas':
        validar_diapositivas(contenido)
    else:
        paginas = contenido.get('paginas')
        if not isinstance(paginas, list) or not 1 <= len(paginas) <= 50:
            raise RecursoInvalido('La encuesta debe tener entre 1 y 50 páginas.')
        ids = set()
        total = 0
        for pagina in paginas:
            if not isinstance(pagina, dict):
                raise RecursoInvalido('Página no válida.')
            texto(pagina.get('titulo', ''), 250, publicable)
            texto(pagina.get('descripcion', ''), 5000)
            preguntas = pagina.get('preguntas')
            if not isinstance(preguntas, list) or not preguntas:
                raise RecursoInvalido('Cada página debe tener al menos una pregunta.')
            for p in preguntas:
                if not isinstance(p, dict):
                    raise RecursoInvalido('Pregunta no válida.')
                total += 1
                identificador = texto(p.get('id'), 80, True)
                if identificador in ids:
                    raise RecursoInvalido('Las preguntas deben tener identificadores distintos.')
                ids.add(identificador)
                texto(p.get('titulo'), 500, publicable)
                texto(p.get('ayuda', ''), 2000)
                if not isinstance(p.get('tipo'), str) or p.get('tipo') not in TIPOS_PREGUNTA or type(p.get('obligatoria')) is not bool:
                    raise RecursoInvalido('Revisa el tipo y la obligatoriedad de las preguntas.')
                if p['tipo'] in {'unica', 'multiple', 'desplegable'}:
                    opciones = p.get('opciones')
                    if not isinstance(opciones, list) or not (2 if publicable else 0) <= len(opciones) <= 50:
                        raise RecursoInvalido('Añade entre 2 y 50 opciones.')
                    opciones = [texto(o, 250, True) for o in opciones]
                    if len(set(opciones)) != len(opciones) or opciones != p['opciones']:
                        raise RecursoInvalido('Las opciones deben ser distintas y no tener espacios exteriores.')
                _validar_exclusivas(p)
                if p['tipo'] == 'escala':
                    if type(p.get('minimo')) is not int or type(p.get('maximo')) is not int:
                        raise RecursoInvalido('La escala necesita límites enteros.')
                    if not 0 <= p['minimo'] < p['maximo'] <= 10:
                        raise RecursoInvalido('La escala debe estar entre 0 y 10.')
        validar_imagenes_encuesta(contenido, publicable=publicable)
        if total > 300:
            raise RecursoInvalido('La encuesta admite hasta 300 preguntas.')
    return {'tipo': tipo, 'titulo': titulo, 'descripcion': descripcion, 'contenido': contenido}

def validar_diapositivas(contenido):
    slides = contenido.get('slides')
    if not isinstance(slides, list) or not 1 <= len(slides) <= 100:
        raise RecursoInvalido('La presentación debe tener entre 1 y 100 diapositivas.')
    for slide in slides:
        if not isinstance(slide, dict):
            raise RecursoInvalido('Diapositiva no válida.')
        texto(slide.get('title', ''), 500)
        texto(slide.get('crumb', ''), 500)
        texto(slide.get('note', ''), 10000)
        items = slide.get('items')
        if not isinstance(items, list) or len(items) > 100:
            raise RecursoInvalido('Contenido de diapositiva no válido.')
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('type'), str) or item.get('type') not in {'t', 'i', 'f'}:
                raise RecursoInvalido('Sólo se admiten elementos de texto, imagen y figuras.')
            for campo in ('x', 'y', 'w', 'h', 'size'):
                v = item.get(campo, 24)
                if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 5000:
                    raise RecursoInvalido('Dimensiones de diapositiva no válidas.')
            enlace_seguro(item.get('href', ''))
            _validar_estilo_elemento(item)
            if item['type'] == 't':
                texto(item.get('text', ''), 20000)
            elif item['type'] == 'f':
                _validar_figura(item)
            else:
                src = item.get('src', '')
                if not isinstance(src, str) or len(src) > 4_000_000 or not re.fullmatch(
                    r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+', src
                ):
                    raise RecursoInvalido('Usa imágenes PNG, JPEG o WebP incrustadas.')

def _validar_figura(item):
    if not isinstance(item.get('figure'), str) or item['figure'] not in {
        'arrow', 'double-arrow', 'line', 'rectangle', 'ellipse', 'triangle', 'diamond', 'check', 'cross', 'bracket',
    }:
        raise RecursoInvalido('Selecciona una figura de la biblioteca.')
    for campo, defecto in (('strokeRole', 'accent'), ('fillRole', 'none')):
        if not isinstance(item.get(campo, defecto), str) or item.get(campo, defecto) not in {
            'primary', 'secondary', 'accent', 'contrast', 'custom', *({'none'} if campo == 'fillRole' else set()),
        }:
            raise RecursoInvalido('Revisa los colores de la figura.')
    for campo in ('strokeColor', 'fillColor'):
        if campo in item and (not isinstance(item[campo], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', item[campo])):
            raise RecursoInvalido('Revisa el color personalizado de la figura.')
    for campo, minimo, maximo in (('strokeWidth', 1, 24), ('bend', -80, 80), ('fillOpacity', 0, 100), ('arrowHead', 8, 48)):
        if campo in item and (type(item[campo]) not in (int, float) or not math.isfinite(item[campo]) or not minimo <= item[campo] <= maximo):
            raise RecursoInvalido(f'Revisa la figura: {campo}.')
    if 'dashed' in item and type(item['dashed']) is not bool:
        raise RecursoInvalido('Revisa el trazo de la figura.')

def _validar_estilo_elemento(item):
    for campo, minimo, maximo in (
        ('opacity', 0, 100), ('lineHeight', .8, 3), ('letterSpacing', -2, 12),
        ('borderWidth', 0, 16), ('brightness', 25, 200), ('contrast', 25, 200),
    ):
        if campo in item:
            valor = item[campo]
            if type(valor) not in (int, float) or not math.isfinite(valor) or not minimo <= valor <= maximo:
                raise RecursoInvalido(f'Revisa el estilo del elemento: {campo}.')
    for campo, permitidos in (
        ('shape', {'rectangle', 'rounded', 'ellipse', 'diamond'}),
        ('fit', {'contain', 'cover'}), ('effect', {'none', 'grayscale', 'sepia'}),
        ('shadow', {'none', 'soft', 'strong'}),
    ):
        if campo in item and (not isinstance(item[campo], str) or item[campo] not in permitidos):
            raise RecursoInvalido(f'Revisa el estilo del elemento: {campo}.')
    for campo in ('underline', 'flipX', 'flipY'):
        if campo in item and type(item[campo]) is not bool:
            raise RecursoInvalido(f'Revisa el estilo del elemento: {campo}.')
    if 'borderColor' in item and (
        not isinstance(item['borderColor'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', item['borderColor'])
    ):
        raise RecursoInvalido('Revisa el color del borde del elemento.')

def validar_respuestas(contenido, respuestas):
    if not isinstance(respuestas, dict):
        raise RecursoInvalido('Envía las respuestas de la encuesta completa.')
    preguntas = [p for pagina in contenido['paginas'] for p in pagina['preguntas']]
    if set(respuestas) - {p['id'] for p in preguntas}:
        raise RecursoInvalido('Hay respuestas para preguntas que no pertenecen a la encuesta.')
    limpias = {}
    for p in preguntas:
        valor = respuestas.get(p['id'])
        if valor is None or valor == '' or valor == []:
            if p['obligatoria']:
                raise RecursoInvalido(f"Responde la pregunta: {p['titulo']}")
            continue
        tipo = p['tipo']
        if tipo in {'texto', 'parrafo', 'correo', 'fecha'}:
            valor = texto(valor, 10000 if tipo == 'parrafo' else 1000, True)
            if tipo == 'correo' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', valor):
                raise RecursoInvalido('Revisa la dirección de correo.')
            if tipo == 'fecha':
                try:
                    date.fromisoformat(valor)
                except ValueError as exc:
                    raise RecursoInvalido('Revisa la fecha.') from exc
        elif tipo in {'unica', 'desplegable'}:
            if not isinstance(valor, str) or valor not in p['opciones']:
                raise RecursoInvalido('Selecciona una opción válida.')
        elif tipo == 'multiple':
            if not isinstance(valor, list) or any(not isinstance(v, str) for v in valor):
                raise RecursoInvalido('Selecciona opciones válidas.')
            if len(set(valor)) != len(valor) or set(valor) - set(p['opciones']):
                raise RecursoInvalido('Selecciona opciones válidas sin repetirlas.')
            if len(valor) > 1 and any(v in p.get('exclusivas', []) for v in valor):
                raise RecursoInvalido(f"Revisa la pregunta «{p['titulo']}»: la opción excluyente debe marcarse sola.")
        else:
            if type(valor) not in (int, float) or not math.isfinite(valor) or abs(valor) > 1e12:
                raise RecursoInvalido('Introduce un número válido.')
            if tipo == 'escala' and (type(valor) is not int or not p['minimo'] <= valor <= p['maximo']):
                raise RecursoInvalido('Elige un valor dentro de la escala.')
        limpias[p['id']] = valor
    return limpias

def resultados(contenido, respuestas):
    salida = []
    for pagina in contenido['paginas']:
        for p in pagina['preguntas']:
            valores = [r[p['id']] for r in respuestas if p['id'] in r]
            categorias = p.get('opciones', []) if p['tipo'] in {'unica', 'multiple', 'desplegable'} else []
            if p['tipo'] == 'escala':
                categorias = list(range(p['minimo'], p['maximo'] + 1))
            frecuencias = [
                {'etiqueta': str(c), 'cantidad': sum(c in v if isinstance(v, list) else c == v for v in valores)}
                for c in categorias
            ]
            salida.append({
                'id': p['id'], 'titulo': p['titulo'], 'tipo': p['tipo'],
                'respondidas': len(valores), 'frecuencias': frecuencias,
                'promedio': sum(valores) / len(valores) if valores and p['tipo'] in {'numero', 'escala'} else None,
                'textos': valores if not categorias and p['tipo'] != 'numero' else [],
            })
    return salida
