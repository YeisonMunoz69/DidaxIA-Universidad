"""Normalización conservadora de escritura matemática recibida del teclado o chat.

No interpreta la expresión ni cambia el mensaje guardado. Sólo prepara una copia
para los detectores y para la frontera simbólica, que sigue validando su entrada.
"""

from __future__ import annotations

import re
import unicodedata

_SUPERINDICES = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ˣʸᵗᵇ", "0123456789-+xytb")
_GRUPO_SUPERINDICE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ˣʸᵗᵇ]+")
NUMEROS_ESCRITOS = {
    "cero": 0, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciséis": 16, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21,
    "veintidós": 22, "veintidos": 22, "veintitrés": 23, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
    "veintinueve": 29, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100,
}
_DECENAS = r"treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa"
_UNIDADES = r"uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve"
_NUMEROS_PATRON = "|".join(sorted(map(re.escape, NUMEROS_ESCRITOS), key=len, reverse=True))


def numero_verbal_al_inicio(texto: str) -> str:
    """Convierte un número español acotado sin inferir frases ambiguas."""
    compuesto = re.match(rf"(?:(menos|negativo)\s+)?({_DECENAS})\s+y\s+({_UNIDADES})\b", texto, re.I)
    if compuesto:
        cantidad = NUMEROS_ESCRITOS[compuesto.group(2).lower()] + NUMEROS_ESCRITOS[compuesto.group(3).lower()]
        return ("-" if compuesto.group(1) else "") + str(cantidad)
    simple = re.match(rf"(?:(menos|negativo)\s+)?({_NUMEROS_PATRON})\b", texto, re.I)
    if simple:
        return ("-" if simple.group(1) else "") + str(NUMEROS_ESCRITOS[simple.group(2).lower()])
    return ""


def normalizar_escritura_matematica(texto: str) -> str:
    """Convierte letras matemáticas estilizadas sin perder los exponentes.

    NFKC solo convertiría ``x⁴`` en ``x4``. Proteger primero el superíndice
    conserva la operación, también en ``(x+1)²`` y ``sen(x)²``.
    """
    con_potencias = _GRUPO_SUPERINDICE.sub(
        lambda m: m.group().translate(_SUPERINDICES) if m.group() in ("⁺", "⁻") else "^(" + m.group().translate(_SUPERINDICES) + ")", texto
    )
    return (
        unicodedata.normalize("NFKC", con_potencias)
        .replace("−", "-")
        .replace("–", "-")
        .replace("×", "*")
        .replace("·", "*")
        .replace("÷", "/")
        .replace("⁄", "/")
        .replace("√", "sqrt")
    )


def normalizar_frase_matematica(expresion: str) -> str:
    """Traduce un vocabulario matemático oral acotado a notación corriente.

    Una frase ambigua, como «seno de equis al cuadrado» sin paréntesis, se
    conserva para pedir precisión; no se elige entre seno de un cuadrado y
    cuadrado del seno. La frontera simbólica valida el resultado traducido.
    """
    s = normalizar_escritura_matematica(expresion).strip()
    s = re.sub(r"\b(?:equis)\b", "x", s, flags=re.I)
    s = re.sub(rf"\b({_DECENAS})\s+y\s+({_UNIDADES})\b",
               lambda m: str(NUMEROS_ESCRITOS[m.group(1).lower()] + NUMEROS_ESCRITOS[m.group(2).lower()]),
               s, flags=re.I)
    s = re.sub(rf"\b({_NUMEROS_PATRON})\b",
               lambda m: str(NUMEROS_ESCRITOS[m.group().lower()]), s, flags=re.I)
    for patron, simbolo in (
        (r"\bdividid[oa]\s+(?:entre|por)\b|\bsobre\b|\bentre\b", "/"),
        (r"\bmultiplicad[oa]\s+por\b|\bpor\b", "*"),
        (r"\bm[aá]s\b", "+"),
        (r"\bmenos\b", "-"),
        (r"\bal\s+cuadrado\b", "^2"),
        (r"\bal\s+cubo\b", "^3"),
        (r"\ba\s+la\s+cuarta\b", "^4"),
    ):
        s = re.sub(patron, simbolo, s, flags=re.I)

    # Sólo funciones con argumento delimitado o atómico. Una composición
    # verbal sin paréntesis no posee una lectura matemática única.
    if re.search(r"\b(?:seno|coseno|tangente|raíz cuadrada)\s+de\s+x\s*\^", s, re.I):
        return s
    for palabra, funcion in (("seno", "sen"), ("coseno", "cos"),
                              ("tangente", "tan"), ("raíz cuadrada", "sqrt")):
        s = re.sub(rf"\b{palabra}\s+de\s+(\([^()]+\)|x\b)",
                   lambda m, nombre=funcion: f"{nombre}({m.group(1).strip('()')})", s, flags=re.I)
    return re.sub(r"\s*([+\-*/^])\s*", r"\1", s).strip()


def quitar_delimitadores_matematicos(texto: str) -> str:
    """Retira sólo envolturas completas de escritura, sin reparar fórmulas."""
    s = texto.strip()
    for inicio, fin in (("$$", "$$"), ("$", "$"), (r"\(", r"\)"), (r"\[", r"\]")):
        if s.startswith(inicio) and s.endswith(fin) and len(s) >= len(inicio) + len(fin):
            return s[len(inicio):-len(fin)].strip()
    return s
