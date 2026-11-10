"""
intervencion.py — La jerarquía de intervención de la tensión `T6` (`PM-B13`)
==============================================================================

`ERS-07` §T6 y `RF-ORQ-04`: el orquestador ejecuta **como máximo una
intervención conductual por turno**, resuelta por una jerarquía ordinal de
cinco niveles — no por magnitud, `ADR-003` C2. Es la **segunda mitad** del
filtro 6: `divulgacion.py` responde **cuánto** se revela, este módulo responde
**qué** se hace. Las dos leen el mismo `Señales` (ver su docstring) porque
miran el mismo turno.

La jerarquía, con la errata `E-01` ya corregida
--------------------------------------------------
`03-Registro-de-Riesgos-OE2.md` E-01: el orden original de `T6` ponía
*«ninguna de las anteriores»* en el nivel 4, **antes** de la ansiedad
explícita. Una condición que absorbe todo lo que no matcheó antes hace que
nada después de ella se alcance nunca — así que la ansiedad expresada
explícitamente, el constructo que da título al proyecto, no se habría
atendido jamás. La corrección intercambia los niveles 4 y 5:

| Nivel | Condición | Intervención |
|:--:|---|---|
| 1 | FAH o PS-Anx elevado **y** ausencia de intento | Andamiaje de primer paso |
| 2 | Ciclo de retroalimentación negativa (`RF-DET-22`) | Ruptura del ciclo, formato Intérprete |
| 3 | Autoeficacia estimada baja | Refuerzo vinculado a un logro concreto |
| 4 | Ansiedad expresada explícitamente | Reencuadre no punitivo del error |
| 5 | Ninguna de las anteriores · **por defecto** | Prompt de autorregulación o metacognición |

El nivel 5 es el que absorbe lo no resuelto, y por eso va **al final**: es la
única posición donde un "catch-all" no le quita el turno a nada.

Por qué el nivel 1 combina dos señales con «y», y las demás no
-------------------------------------------------------------------
Solo el nivel 1 es una conjunción. Es la posición que `T6` reserva para el
bloqueo previo al intento —FAH bloquea que la interacción se inicie, `ADR-003`
C3—, y esa es justamente la situación en la que **el estudiante ansioso que sí
lo intentó** no debe leerse: si ya hay intento, el ciclo negativo o la
autoeficacia (niveles 2 y 3) son la lectura correcta de una ansiedad que no
paralizó, y `T6` los coloca antes por eso.

`None` no es «no», aquí también
-----------------------------------
Igual que en `divulgacion.py`: mientras el filtro 3 (`PM-B10`) no exista,
`ansiedad_alta`, `miedo_a_pedir_ayuda_alto`, `ciclo_negativo`,
`autoeficacia_baja` y `ansiedad_explicita` llegan en `None`. Una condición en
`None` no se da por cumplida —eso inventaría una intervención sin evidencia—
ni se descarta —eso escondería que no se pudo evaluar—: se dice, en
`sin_evaluar`, y la comprobación sigue con el siguiente nivel.
"""

from __future__ import annotations

from dataclasses import dataclass

from dominio.arbitraje.divulgacion import Señales

#: Los cinco niveles de `T6`, ya con la corrección de `E-01` aplicada. El 5 es
#: el piso y el defecto — nunca el 4, que es donde estaba el error.
BLOQUEO_SIN_INTENTO = 1
CICLO_NEGATIVO = 2
AUTOEFICACIA_BAJA = 3
ANSIEDAD_EXPLICITA = 4
AUTORREGULACION = 5

NOMBRE_INTERVENCION = {
    BLOQUEO_SIN_INTENTO: "andamiaje de primer paso",
    CICLO_NEGATIVO: "ruptura del ciclo, formato Intérprete",
    AUTOEFICACIA_BAJA: "refuerzo vinculado a un logro concreto",
    ANSIEDAD_EXPLICITA: "reencuadre no punitivo del error",
    AUTORREGULACION: "autorregulación o metacognición",
}


@dataclass(frozen=True)
class DecisionIntervencion:
    """El nivel de `T6`, por qué, y qué otras condiciones activas se
    descartaron —`RF-REG-06` pide el estrato de decisión completo, y esto es
    la mitad de «qué se hace» de ese estrato."""

    nivel: int
    motivo: str
    descartadas: tuple[str, ...] = ()
    sin_evaluar: tuple[str, ...] = ()

    @property
    def nombre(self) -> str:
        return NOMBRE_INTERVENCION.get(self.nivel, NOMBRE_INTERVENCION[AUTORREGULACION])


def _nivel_1_bloqueo_sin_intento(
    señales: Señales, sin_evaluar: list[str]
) -> tuple[int, str] | None:
    """La única condición compuesta de la jerarquía: exige FAH o PS-Anx
    elevado **y** ausencia de intento a la vez, así que no encaja en el
    patrón de un solo campo que usan los demás niveles."""
    if señales.miedo_a_pedir_ayuda_alto is None:
        sin_evaluar.append("miedo a pedir ayuda (sin modelo del estudiante · filtro 3)")
    if señales.ansiedad_alta is None:
        sin_evaluar.append("ansiedad alta (sin modelo del estudiante · filtro 3)")

    elevada = bool(señales.miedo_a_pedir_ayuda_alto) or bool(señales.ansiedad_alta)
    if elevada and señales.intentos_en_el_problema == 0:
        return BLOQUEO_SIN_INTENTO, "FAH o PS-Anx elevado sin intento"
    return None


def _nivel_de_un_campo(
    valor: bool | None, nivel: int, motivo: str, campo: str, sin_evaluar: list[str]
) -> tuple[int, str] | None:
    """Los niveles 2 a 4: un solo campo booleano, `None` = sin fuente."""
    if valor:
        return nivel, motivo
    if valor is None:
        sin_evaluar.append(f"{campo} (sin modelo del estudiante · filtro 3)")
    return None


def decidir_intervencion(señales: Señales) -> DecisionIntervencion:
    """La intervención de `T6` para este turno, en el orden corregido por `E-01`.

    A diferencia de `divulgacion.decidir` —que comprueba de mayor a menor
    porque busca «cuánto» revelar como máximo—, aquí se comprueba en el orden
    **de precedencia** de la jerarquía, de 1 a 5, y gana la condición de
    **menor** número: es lo que hace que la posición en la tabla sea la
    prioridad, `ADR-003` C2.
    """
    sin_evaluar: list[str] = []
    candidatos = (
        _nivel_1_bloqueo_sin_intento(señales, sin_evaluar),
        _nivel_de_un_campo(
            señales.ciclo_negativo,
            CICLO_NEGATIVO,
            "ciclo de retroalimentación negativa",
            "ciclo negativo",
            sin_evaluar,
        ),
        _nivel_de_un_campo(
            señales.autoeficacia_baja,
            AUTOEFICACIA_BAJA,
            "autoeficacia estimada baja",
            "autoeficacia",
            sin_evaluar,
        ),
        # El nivel que `E-01` rescató: si cayera detrás de un catch-all, no
        # se alcanzaría jamás. Va antes que el defecto y solo antes que él.
        _nivel_de_un_campo(
            señales.ansiedad_explicita,
            ANSIEDAD_EXPLICITA,
            "ansiedad expresada explícitamente",
            "ansiedad explícita",
            sin_evaluar,
        ),
    )
    activas = [c for c in candidatos if c is not None]

    if not activas:
        return DecisionIntervencion(
            nivel=AUTORREGULACION,
            motivo="ninguna condición de T6 se cumple: la autorregulación es el defecto",
            sin_evaluar=tuple(sin_evaluar),
        )

    ganadora = min(activas, key=lambda par: par[0])
    descartadas = tuple(
        motivo for nivel, motivo in activas if (nivel, motivo) != ganadora
    )
    return DecisionIntervencion(
        nivel=ganadora[0],
        motivo=ganadora[1],
        descartadas=descartadas,
        sin_evaluar=tuple(sin_evaluar),
    )
