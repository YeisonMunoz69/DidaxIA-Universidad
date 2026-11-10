"""Gramática acotada de expresiones dictadas; no calcula ni completa lo omitido.

Funciones sin paréntesis consumen un monomio. Las composiciones con alcance
ambiguo requieren delimitadores explícitos. Toda la entrada debe consumirse.
"""
import re
import unicodedata

from dominio.modelo.notacion_entrada import NUMEROS_ESCRITOS, normalizar_escritura_matematica


class LecturaIncierta(ValueError):
    pass


def _tokens(texto):
    s = normalizar_escritura_matematica(texto).lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))
    for palabra, numero in sorted(NUMEROS_ESCRITOS.items(), key=lambda p: -len(p[0])):
        s = re.sub(rf'\b{palabra}\b', str(numero), s)
    s = re.sub(r'\bequis\b', 'x', s)
    for patron, cambio in (
        (r'\blogaritmo\s+en\s+base\s+(\d+)\s+de\b', r'logbase\1'),
        (r'\blogaritmo\s+natural\s+de\b', 'ln'),
        (r'\b(?:raiz(?:\s+cuadrada)?|seno|coseno|tangente|arcotangente)\s+de\b',
         lambda m: {'raiz': 'sqrt', 'seno': 'sin', 'coseno': 'cos', 'tangente': 'tan', 'arcotangente': 'atan'}[m[0].split()[0]]),
        (r'\bal\s+cuadrado\b', '^2'), (r'\bal\s+cubo\b', '^3'),
        (r'\ba\s+la\s+cuarta\b', '^4'),
        (r'\belevado\s+a(?:\s+la)?\b|\be\s+a\s+la\b', lambda m: 'e^' if m[0].startswith('e a') else '^'),
        (r'\bmultiplicad[oa]\s+por\b|\bpor\b', '*'),
        (r'\bsobre\b|\bdividid[oa]\s+entre\b', '/'),
        (r'\bmas\b', '+'), (r'\bmenos\b', '-'),
    ):
        s = re.sub(patron, cambio, s)
    # En una potencia dictada, el exponente puede ser un monomio completo.
    s = re.sub(r'\^\s*([-+]?\s*\d*\s*[xteu])\b', r'^(\1)', s)
    tokens = re.findall(r'logbase\d+|sqrt|sin|cos|tan|atan|exp|ln|log|\d+(?:\.\d+)?|[xteu]|[()+*/^,-]', s)
    if ''.join(tokens) != re.sub(r'\s+', '', s):
        raise LecturaIncierta('La expresión contiene palabras cuyo alcance no está delimitado.')
    return tokens


class _Expresion:
    def __init__(self, tokens):
        if not tokens or len(tokens) > 180:
            raise LecturaIncierta('La expresión está vacía o es demasiado extensa.')
        self.tokens = tokens
        self.pos = 0

    def actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ''

    def tomar(self):
        t = self.actual()
        self.pos += 1
        return t

    def expresion(self, minimo=0, profundidad=0):
        if profundidad > 24:
            raise LecturaIncierta('Demasiados niveles de agrupación.')
        izquierda = self.atomo(profundidad + 1)
        while self.actual() and self.actual() not in (')', ','):
            operador = self.actual()
            implicito = operador not in ('+', '-', '*', '/', '^')
            if implicito:
                operador = '*'
            poder = 25 if implicito else {'+': 10, '-': 10, '*': 20, '/': 20, '^': 30}[operador]
            if poder < minimo:
                break
            if not implicito:
                self.tomar()
            derecha = self.expresion(poder if operador == '^' else poder + 1, profundidad + 1)
            izquierda = f'({izquierda}{operador}{derecha})'
        return izquierda

    def atomo(self, profundidad):
        t = self.tomar()
        if t in ('+', '-'):
            return f'({t}{self.expresion(30, profundidad + 1)})'
        if t == '(':
            r = self.expresion(0, profundidad + 1)
            if self.tomar() != ')':
                raise LecturaIncierta('Falta cerrar un paréntesis.')
            return r
        if re.fullmatch(r'\d+(?:\.\d+)?|[xteu]', t):
            return t
        if t in ('sqrt', 'sin', 'cos', 'tan', 'atan', 'exp', 'ln', 'log') or t.startswith('logbase'):
            # Con paréntesis, todo el grupo; sin ellos, un monomio (p. ej. sin 5x).
            argumento = self.atomo(profundidad + 1) if self.actual() == '(' else self.monomio(profundidad + 1)
            return f'log({argumento},{t[7:]})' if t.startswith('logbase') else f'{t}({argumento})'
        raise LecturaIncierta('Falta un argumento o hay un operador inesperado.')

    def monomio(self, profundidad):
        primero = self.actual()
        r = self.atomo(profundidad + 1)
        if re.fullmatch(r'\d+(?:\.\d+)?', primero) and self.actual() in ('x', 't', 'u'):
            r = f'({r}*{self.expresion(30, profundidad + 1)})'
        elif self.actual() == '^':
            self.tomar()
            r = f'({r}^{self.expresion(30, profundidad + 1)})'
        return r


def expresion_oral(texto, *, composicion_contextual=False):
    if not composicion_contextual and re.search(r'\b(?:seno|coseno|tangente)\s+de\s+(?:seno|coseno|tangente)\b', texto, re.I):
        raise LecturaIncierta('La composición de funciones necesita paréntesis para fijar el alcance.')
    partes = re.split(r',?\s*todo\s+sobre\s+', texto, maxsplit=1, flags=re.I)
    if len(partes) == 2:
        return f'({expresion_oral(partes[0])})/({expresion_oral(partes[1])})'
    p = _Expresion(_tokens(texto))
    resultado = p.expresion()
    if p.pos != len(p.tokens):
        raise LecturaIncierta('Sobran símbolos o falta una agrupación.')
    return resultado


def leer_tarea_oral(mensaje):
    """(notación, aclaración). El mensaje original se conserva en el historial."""
    oral = re.search(r'\bal\s+(?:cuadrado|cubo)\b|\bra[ií]z\b|\b(?:seno|coseno|tangente|arcotangente|logaritmo)\b|\be\s+(?:elevado|a\s+la)|\belevado\s+a|\bpor\s+la\s+(?:derecha|izquierda)\b|\bsobre\b|\bmas\b|\bmenos\b', mensaje, re.I)
    if not oral:
        return '', ''
    try:
        return _tarea_oral(mensaje), ''
    except LecturaIncierta:
        return '', 'Para asegurar qué expresión quieres trabajar, escríbela con notación matemática y paréntesis. Así evitamos cambiar el alcance de una raíz, potencia o división. ¿Cómo quedaría tu expresión?'


def _tarea_oral(mensaje):
    derivada = re.search(r'\b(?:(primera|segunda|tercera)\s+)?derivada\s+de\s+(.+)', mensaje, re.I)
    if derivada:
        orden = {'segunda': 2, 'tercera': 3}.get((derivada[1] or '').lower(), 1)
        ordinal = {1: 'primera', 2: 'segunda', 3: 'tercera'}[orden]
        return f'{ordinal} derivada de {expresion_oral(derivada[2])}'
    cuando = r'(?:x\s+)?(?:tiende|se\s+acerca)\s+a\s+'
    limite = re.search(r'\bl[ií]mite\s+(?:de\s+x\s+)?cuando\s+' + cuando + r'(.+?)\s+de\s+(.+)', mensaje, re.I)
    if limite:
        destino, expr = limite[1], limite[2]
    else:
        limite = re.search(r'\bl[ií]mite\s+de\s+(.+?)\s+cuando\s+' + cuando + r'(.+)', mensaje, re.I)
        if not limite:
            return ''
        expr, destino = limite[1], limite[2]
    lado = '+' if re.search(r'por\s+la\s+derecha', destino, re.I) else ('-' if re.search(r'por\s+la\s+izquierda', destino, re.I) else '')
    destino = re.sub(r'\s+por\s+la\s+(?:derecha|izquierda).*', '', destino, flags=re.I).strip()
    destino = destino.lower().replace('menos infinito', '-oo').replace('infinito', 'oo')
    if destino not in ('oo', '-oo'):
        destino = expresion_oral(destino)
        destino = destino.strip('()')
    return f'lim (x->{destino}{lado}) {expresion_oral(expr)}'
