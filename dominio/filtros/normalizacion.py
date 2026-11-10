"""
normalizacion.py — Filtro 1 · normalización de la entrada
===========================================================

`ADR-007` adoptó el **canal dual**: el turno no es texto, son dos lenguajes
entrelazados —prosa y expresión matemática— y se separan **antes** de
interpretarlos, con cascada determinista-primero (alternativa C, §6). Este
filtro es el que hace esa separación.

Qué hace, en el orden de `ADR-007` §6.2
----------------------------------------
**N1 · Segmentación primero.** Se localizan las expresiones candidatas por
marcadores léxicos y sintácticos —función, notación de derivada, delimitador
de LaTeX, operador entre alfanuméricos— y se registran con su desplazamiento
en la traza, para poder recombinarlas después.

**N2 · Normalización determinista.** Cada expresión se lleva a forma canónica
por sustitución léxica: `\\times`/`\\cdot` y las palabras españolas del
operador se llevan a su símbolo, y las tres notaciones de derivada de
`RF-IUC-02` —`d/dx(·)`, `\\frac{d}{dx}(·)` y `f'(x)`/`df/dx`— se llevan a una
forma común dentro de cada pareja.

**N4 · La normalización no destruye el texto.** `ctx.texto_estudiante` no se
toca. La forma canónica se **añade** en `ctx.expresiones`, no sustituye nada.

Lo que este filtro NO hace, y por qué se queda corto a propósito
------------------------------------------------------------------
**N3 · «el modelo propone, el CAS dispone»** no está aquí: no hay modelo
conectado a este filtro. Cuando la sustitución léxica no resuelve una
expresión, se marca `notacion_no_resuelta` y se deja la original — no se
esconde, no se inventa una forma.

**`R-20` sigue sin medir.** La segmentación **no está validada sobre lenguaje
espontáneo**: localizar dónde empieza y acaba una expresión dentro de una
frase en español es exactamente lo que `R-20` registra como riesgo alto. Este
filtro no lo resuelve — la regla «el modelo propone, el CAS dispone» acota el
daño de un error de segmentación, no lo impide. Ninguna prueba de este archivo
afirma que la segmentación sea correcta en general: afirma que es
determinista y que no toca el texto original.
"""

from __future__ import annotations

import re
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno

#: Marcadores léxicos y sintácticos de una expresión candidata (`ADR-007`
#: N1). Es una superposición deliberada con `dominio.modelo.deteccion_matematica`
#: —los dos existen para notar «hay matemática aquí»—, pero este necesita el
#: **tramo completo**, no solo que hubo un acierto, así que no se reutiliza el
#: mismo objeto: se reutiliza el criterio.
#: 🔴 **Fase 4 · la llamada a función deja de cortarse donde empieza a
#: importar.** Hasta aquí la alternativa de función era
#: `(sen|cos|…)\s*\([^)]*\)` y nada más, así que segmentaba:
#:
#: | Escrito | Segmentado | Consecuencia |
#: |---|---|---|
#: | `cos(x)^3` | `cos(x)` | el exponente desaparece: `cos(x)^3` y `cos(x)` son **el mismo problema** para el motor |
#: | `sen(x)*cos(x)` | `sen(x)`, `cos(x)` | dos expresiones donde hay una, y el precómputo deriva la primera mitad |
#: | `cos(x)^2 - sen(x)^2` | `cos(x)`, `sen(x)` | una respuesta correcta no se puede comprobar contra lo que el estudiante escribió |
#:
#: Con la unidad de problema de la fase 4 —que se identifica por la expresión
#: normalizada— eso deja de ser una imprecisión y pasa a ser un error: dos
#: ejercicios distintos comparten contadores. Se extiende **sólo** la
#: alternativa de función, con dos añadidos acotados: un exponente opcional
#: detrás de la llamada, y una cadena de términos unidos por un operador
#: explícito. Sigue haciendo falta un operador para continuar, así que la prosa
#: de alrededor no se traga: «cos(x) me da» corta en el espacio, como antes.
#: 🔴 **Fase 4 R1 · paquete G · el signo unario dejaba de existir.**
#:
#: `-3*cos(x)^2*sen(x)` se segmentaba como `3*cos(x)^2*sen(x)`: ninguna
#: alternativa admitía un signo delante, y el `\b` de la de operador explícito
#: empezaba a contar en el `3`. Y ésa **es** la derivada de `cos(x)^3`, así que
#: perder el menos convertía la respuesta correcta en `invalida` — el peor
#: resultado que el filtro 6.6 puede producir, y el que su propia cabecera
#: declara como el error caro.
#:
#: El signo se toma **sólo cuando es unario**: si delante hay un operando
#: —letra, cifra o paréntesis que cierra— el menos es una resta y pertenece a
#: la cadena que ya se está leyendo, no al término siguiente. La mirada atrás
#: es de un carácter, que es lo que `re` admite con ancho fijo y lo único que
#: hace falta para distinguir `x-1` de «me da -3».
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

# Una respuesta a «¿qué valores usarías?» como «de -3 a 3» es un intervalo
# para tabular, no el monomio «-3 a». No puede sustituir al ejercicio activo.
_RANGO_PARA_TABULAR = re.compile(
    r"\bde\s+[-+]?\d+(?:[.,]\d+)?\s+a\s+[-+]?\d+(?:[.,]\d+)?\b",
    re.IGNORECASE,
)

#: N2 · sustituciones léxicas simples, en el orden en que se aplican. Nada de
#: esto pasa por un CAS: son reemplazos de texto, deterministas y baratos.
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
    """N2 · las tres parejas de `RF-IUC-02`, llevadas a una forma común.

    Cada rama produce la misma forma que su pareja: `d/dx(·)` con
    `\\frac{d}{dx}(·)`, y `f'(x)` con `df/dx`. Las dos parejas **no** se
    igualan entre sí — el criterio de aceptación no lo pide, solo que cada
    pareja coincida consigo misma.
    """
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
    """Forma canónica de una expresión, y si N2 la resolvió.

    `resuelta` no afirma que la expresión esté bien escrita: afirma que **una
    regla de reescritura determinista se aplicó**. Una llamada a función como
    `sen(x^2)` puede quedar intacta y aun así marcarse `resuelta=False`,
    porque ninguna regla de este archivo tuvo que tocarla — no hay aquí (ni
    en `N3`, que no está conectado) nada que confirme que es correcta, solo
    que se segmentó. `resuelta=False` es la marca `notacion_no_resuelta` de
    `ADR-007`: la expresión original se conserva, no se descarta y no se
    fuerza una forma.
    """
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
    """Las expresiones del texto en forma canónica, con su rastro · N1 + N2.

    Es el cuerpo del filtro 1, expuesto aparte **para que el borde pueda
    preguntar lo mismo sin duplicar el criterio** — igual que
    `FiltroEnrutamiento` reutiliza `identificar_nodo()` del recuperador en vez
    de copiar su cascada léxica. `adaptadores/entrantes/http/rutas/turno.py` la
    usa para recordar en la sesión la última expresión que el estudiante
    escribió (`PM-B31`); dos segmentadores que pudieran discrepar serían dos
    ideas distintas de qué es una expresión.
    """
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
    # El segmentador general puede hallar sólo un fragmento de una definición
    # por tramos, o incluir `y=` en vez del lado derecho. Una petición explícita
    # de gráfica con definición completa tiene precedencia sobre esos trozos.
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
    """Filtro 1 de `ADR-001` §6.3."""

    nombre = "normalización de la entrada"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        expresiones, segmentos = segmentar(ctx.texto_estudiante)

        # `PM-B31`, 2026-08-13 · si este turno no trae ninguna expresión pero la
        # conversación venía de una, se hereda.
        #
        # **Lo destapó una medición, no una prueba.** `E04` mostró un turno de
        # nivel 3 —«sigo sin verlo, qué hago con lo de adentro»— en el que el
        # generador falló y el respaldo determinista de `D-21` **no pudo
        # entrar**: sin expresión en ESE mensaje no hay precómputo con el que
        # respaldar. Y es el caso típico, no el raro: el estudiante escribe
        # `sen(x^2)` una vez y luego habla de «lo de adentro».
        #
        # Se hereda **solo cuando no segmentó nada**, así que escribir una
        # expresión nueva siempre gana. El peor caso es que el turno hable del
        # ejercicio anterior, que es del que venía hablando.
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
        # N4: `texto_estudiante` no se toca. Solo se añade `expresiones`.
        return replace(
            ctx, expresiones=expresiones, expresiones_heredadas=bool(heredada)
        ), meta
