from __future__ import annotations

import re
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno


_SIGNO_UNARIO = r"(?:(?<![\w)])-\s*)?"

_FUNCION = r"(?:sin|sen|cos|tan|tg|log|ln|exp|sqrt|raiz)\s*\([^)]*\)"
_POTENCIA = r"(?:\s*\^\s*(?:\([^)]*\)|[0-9a-zA-Z]+))?"
_TERMINO = rf"(?:{_FUNCION}{_POTENCIA}|\d+(?:\.\d+)?|[a-zA-Z]){_POTENCIA}"

_PATRON_EXPRESION = re.compile(
    rf"""
      \\frac\{{d\}}\{{dx\}}\s*\([^)]*\)                                # \frac{{d}}{{dx}}(·)
    | \\frac\{{d\}}\{{dx\}}\s*[a-zA-Z][a-zA-Z0-9_^]*                    # \frac{{d}}{{dx}}x^2
    | d/dx\s*\([^)]*\)                                                 # d/dx(·)
    | \b[a-zA-Z][a-zA-Z0-9_]*\s*'\s*\([^)]*\)                          # f'(x)
    | \bd[a-zA-Z][a-zA-Z0-9_]*\s*/\s*d[a-zA-Z][a-zA-Z0-9_]*\b          # df/dx
    | {_SIGNO_UNARIO}\b{_FUNCION}{_POTENCIA}(?:\s*[*/+\-]\s*{_TERMINO})*  # función, con signo, potencia y cadena
    | \$[^$]+\$                                                        # $·$
    | \\\([^)]*\\\)                                                    # \(·\)
    | {_SIGNO_UNARIO}\b[a-zA-Z0-9_]+\s*(?:\\times|\\cdot|[*/^=])\s*
        [0-9a-zA-Z().]+(?:\s*[+\-*/^=]\s*[0-9a-zA-Z().]+)*             # operador explícito, con signo
    | {_SIGNO_UNARIO}\b\d+\s*[a-zA-Z]\b                                # monomio simple tipo 2x, con signo
    """,
    re.VERBOSE | re.IGNORECASE,
)


_RANGO_PARA_TABULAR = re.compile(
    r"\bde\s+[-+]?\d+(?:[.,]\d+)?\s+a\s+[-+]?\d+(?:[.,]\d+)?\b",
    re.IGNORECASE,
)


_SUSTITUCIONES_SIMBOLO = (
    (re.compile(r"\\times|\\cdot"), "*"),
    (re.compile(r"\bpor\b", re.IGNORECASE), "*"),
    (re.compile(r"\bdividido\s+(?:por|entre)\b", re.IGNORECASE), "/"),
    (re.compile(r"\bentre\b", re.IGNORECASE), "/"),
    (re.compile(r"\bmás\b", re.IGNORECASE), "+"),
    (re.compile(r"\bmenos\b", re.IGNORECASE), "-"),
    (re.compile(r"\belevado\s+a\b", re.IGNORECASE), "^"),
)

_FRAC_DDX_PARENTESIS = re.compile(r"^\\frac\{d\}\{dx\}\s*\(([^)]*)\)$")
_FRAC_DDX_SIMPLE = re.compile(r"^\\frac\{d\}\{dx\}\s*([a-zA-Z][a-zA-Z0-9_^]*)$")
_DDX_PARENTESIS = re.compile(r"^d/dx\s*\(([^)]*)\)$")
_PRIMA = re.compile(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*'\s*\([^)]*\)$")
_COCIENTE_DIFERENCIAL = re.compile(r"^d([a-zA-Z][a-zA-Z0-9_]*)\s*/\s*d[a-zA-Z][a-zA-Z0-9_]*$")


def _normalizar_derivada(expresion: str) -> str | None:
    m = _FRAC_DDX_PARENTESIS.match(expresion) or _DDX_PARENTESIS.match(expresion)
    if m:
        return f"d/dx({m.group(1).strip()})"
    m = _FRAC_DDX_SIMPLE.match(expresion)
    if m:
        return f"d/dx({m.group(1).strip()})"
    if _PRIMA.match(expresion) or _COCIENTE_DIFERENCIAL.match(expresion):
        return "d/dx(f)"
    return None

def _normalizar(expresion: str) -> tuple[str, bool]:
    derivada = _normalizar_derivada(expresion.strip())
    if derivada is not None:
        return derivada, True

    forma = expresion
    cambiada = False
    for patron, simbolo in _SUSTITUCIONES_SIMBOLO:
        nueva = patron.sub(simbolo, forma)
        if nueva != forma:
            cambiada = True
        forma = nueva
    return forma.strip(), cambiada

def segmentar(texto: str) -> tuple[tuple[str, ...], list[dict]]:
    expresiones: list[str] = []
    segmentos: list[dict] = []
    rangos = tuple(_RANGO_PARA_TABULAR.finditer(texto))
    for coincidencia in _PATRON_EXPRESION.finditer(texto):
        if any(rango.start() <= coincidencia.start() < rango.end() for rango in rangos):
            continue
        original = coincidencia.group(0)
        forma_canonica, resuelta = _normalizar(original)
        expresiones.append(forma_canonica)
        segmentos.append(
            {
                "inicio": coincidencia.start(),
                "fin": coincidencia.end(),
                "original": original,
                "forma_canonica": forma_canonica,
                "resuelta": resuelta,
            }
        )

    peticion = re.search(
        r"\b(?:graf[ií]ca\w*|grafic\w*|dibuj\w*|representa\w*)\b",
        texto,
        re.IGNORECASE,
    )
    if peticion:
        resto = texto[peticion.end():]
        definicion = re.search(r"\b(?:[a-zA-Z]\s*(?:\\left\s*)?\([^)]*\)|y)\s*=\s*(.+)$", resto, re.IGNORECASE)
        if definicion is None:
            definicion = re.search(r"\bfunci[oó]n\s+(.+)$", resto, re.IGNORECASE)
        if definicion:
            original = definicion.group(1).strip()
            original = re.split(
                r"\s+y\s+(?:expl[ií]ca\w*|dime\b|mu[eé]strame\b|cu[eé]ntame\b|c[oó]mo\b|qu[eé]\b)",
                original,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].rstrip(".?! ")
            if original:
                inicio = peticion.end() + definicion.start(1)
                expresiones = [original]
                segmentos = [{
                    "inicio": inicio,
                    "fin": inicio + len(original),
                    "original": original,
                    "forma_canonica": original,
                    "resuelta": False,
                }]
    return tuple(expresiones), segmentos

class FiltroNormalizacion(Filtro):

    nombre = "normalización de la entrada"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        expresiones, segmentos = segmentar(ctx.texto_estudiante)

        heredada = ""
        if not expresiones and ctx.expresion_previa:
            heredada = ctx.expresion_previa
            expresiones = (heredada,)

        meta = {
            "expresiones_encontradas": len(expresiones),
            "segmentos": segmentos,
            "no_resueltas": sum(1 for s in segmentos if not s["resuelta"]),
        }
        if heredada:
            meta["heredada_de_la_sesion"] = heredada

        return replace(
            ctx, expresiones=expresiones, expresiones_heredadas=bool(heredada)
        ), meta
