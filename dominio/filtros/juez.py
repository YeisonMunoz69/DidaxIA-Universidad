"""
juez.py — Filtro 10 · evaluación por juez
=============================================

`ADR-001` §6.3 lo pone en ruta caliente y con una etiqueta que no admite
lectura ambigua: **«complementaria, nunca sustitutiva de la verificación
simbólica»**. El filtro 9 ya decidió qué nivel se emite y si las afirmaciones
declaradas son correctas; este filtro **no puede cambiar ninguna de las dos
cosas**. Cierra lo que quedaba de `PM-B12` — es, junto a normalización e
intención, el último de los filtros que no depende del modelo del
estudiante, y por eso entra en esta sesión y los de los incrementos 5 y 6 no.

Dónde empieza este filtro y dónde termina el 9
------------------------------------------------
El CAS de `verificacion.py` comprueba **matemática declarada en bloque**:
que `2*x*cos(x^2)` equivalga a lo que el fragmento afirma. Eso es todo lo que
un motor de álgebra puede juzgar, y es exactamente su frontera.

Lo que ningún CAS puede leer es **la prosa alrededor de esos bloques** — el
texto que el estudiante realmente lee—, y ahí hay dos reglas que sí se
pueden comprobar sin volver a invocar el motor simbólico:

- **`ERS-01` §6.4**: *«ninguna decisión crítica se delega al LLM generador
  principal»*, que el andamio del filtro 7 traduce en una instrucción
  explícita: *«no presentes ningún resultado matemático como comprobado»*.
  Nada impide que el generador la ignore. Este filtro busca en la prosa —la
  parte de la narración que **no** es una referencia `{{aN}}`— fórmulas de
  certeza absoluta (*«está comprobado», «sin duda es», «definitivamente
  es»*) y las señala. No es una comprobación matemática: es una comprobación
  de **cómo se habla** de la matemática.
- **`08-Contrato-del-Turno.md` §6**: el nivel `sondeo` es *«el sistema
  pregunta en lugar de responder»*. El filtro 9 (regla C4 de `ADR-014`) ya
  garantiza que `sondeo` no lleva afirmaciones declaradas; lo que no
  garantiza es que el texto **suene** a pregunta. Este filtro comprueba que
  la respuesta en `sondeo` contenga al menos una interrogación.

Ninguna de las dos comprobaciones vuelve a mirar si `2x·cos(x²)` es la
derivada correcta — **eso ya lo hizo el 9, y duplicarlo sería exactamente lo
que el encargo de esta sesión pide no hacer.**

Qué hace con lo que encuentra
-------------------------------
**Nada que cambie el turno.** Las advertencias quedan en la traza —es la
propiedad de `RF-ORQ-14` que hace esto complementario en vez de sustitutivo—
y `ctx.respuesta` y `ctx.nivel_divulgacion` salen exactamente como entraron.
Decidir qué hacer con una advertencia —reintentar la generación, descender un
nivel, avisar al docente— es una política que no está encargada esta sesión,
y no se improvisa aquí una a falta de instrucción.

Lo que se queda fuera a propósito
------------------------------------
**Sin modelo conectado**, igual que los filtros 1 y 2 de esta misma sesión:
las dos reglas de arriba son heurísticas léxicas, no un juicio semántico de
si la pedagogía es buena. Conectar un juez basado en modelo es una decisión
de `RNF-EFI-01` —qué presupuesto de latencia le queda a la ruta caliente
después de generación y verificación— y no se toma de paso aquí.
"""

from __future__ import annotations

import re

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno

#: Fórmulas de certeza absoluta sobre un resultado, en la prosa que rodea las
#: referencias verificadas. Cada una está aquí porque es una forma real de
#: reclamar comprobación en español, no porque se me ocurriera que podría
#: aparecer — mismo criterio que `deteccion_matematica.py` declara para su
#: propia lista.
_CERTEZA_ABSOLUTA = re.compile(
    r"est[aá]\s+comprobado|sin\s+duda\s+es|definitivamente\s+es|"
    r"es\s+correcto\s+que|con\s+toda\s+certeza",
    re.IGNORECASE,
)

_PATRON_REFERENCIA = re.compile(r"\{\{\s*[A-Za-z0-9_-]+\s*\}\}")

_INTERROGACION = re.compile(r"[¿?]")


def _prosa_sin_referencias(respuesta: str) -> str:
    """La narración sin los `{{aN}}`: lo que el CAS no comprobó porque no es
    lo que él comprueba, y lo único que este filtro tiene sentido leyendo."""
    return _PATRON_REFERENCIA.sub(" ", respuesta)


class FiltroJuez(Filtro):
    """Filtro 10 de `ADR-001` §6.3."""

    nombre = "juicio complementario"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        advertencias: list[str] = []

        prosa = _prosa_sin_referencias(ctx.respuesta)
        hallazgo = _CERTEZA_ABSOLUTA.search(prosa)
        if hallazgo:
            advertencias.append(
                f"lenguaje de certeza absoluta en la prosa: «{hallazgo.group(0)}» "
                f"(ERS-01 §6.4: ninguna decisión crítica se delega al generador)"
            )

        if ctx.nivel_divulgacion == 1 and not _INTERROGACION.search(ctx.respuesta):
            advertencias.append(
                "nivel «sondeo» sin ninguna interrogación: el contrato exige "
                "preguntar, no afirmar (08-Contrato-del-Turno.md §6)"
            )

        meta = {
            "advertencias": tuple(advertencias),
            "aprobado_por_el_juez": not advertencias,
        }
        # El contexto sale exactamente como entró: este filtro es
        # complementario y nunca sustitutivo, así que no hay `replace()` que
        # cambie `respuesta` ni `nivel_divulgacion`.
        return ctx, meta
