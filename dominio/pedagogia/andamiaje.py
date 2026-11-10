"""
andamiaje.py — Qué contenido de `contenido/plantillas/` usa este turno
=============================================================================

De aquí salen las cinco plantillas de prioridad **M** del contenido —`RC-PED-01`
(APOS), `RC-PED-02` (KQ1–KQ5), `RC-PED-06` (two-tier), `RC-PED-19`
(autoconcepto) y `RC-PED-20` (autorregulación)—: este módulo decide cuál de
ellas ve el generador en cada turno.

🔴 Qué cambió en la fase 4, y por qué era necesario
------------------------------------------------------
Hasta aquí, **este módulo era el selector**: miraba el diagnóstico, las
concepciones candidatas y las señales, y de ahí salía el andamiaje. Y como
todas sus filas terminaban en un repertorio de preguntas, la respuesta del
sistema era socrática pasara lo que pasara — **37 prompts de 43** en el banco
congelado.

Ahora quien decide **qué clase de respuesta** es el turno es
`dominio/pedagogia/politica.py`, y este módulo hace lo que su nombre dice:
traducir esa estrategia al contenido que le corresponde. La tabla se redujo a
una correspondencia, y eso es exactamente lo que se buscaba: la pedagogía
revisable está en la política, aquí queda el vínculo con el contenido.

La correspondencia, y la fila que más importa
------------------------------------------------
| Estrategia | Repertorio principal | Quién lo dice |
|---|---|---|
| `dialogo_socratico_apos` | `P-SOCRATICA-APOS` | `p-socratica-apos.md`: acompaña una transición de nivel |
| `scaffolding_kq` | la `s-mXX` de la concepción si la hay; si no, `P-KQ1-KQ5` | `p-scaffolding-kq1-kq5.md` §Cómo se parametriza |
| `conflicto_conceptual` | la `s-mXX` diagnosticada o candidata; si no, `P-KQ1-KQ5` | `p-two-tier.md` §Qué sigue, fila `E4` |
| **todas las demás** | **ninguno** | ver abajo |

**«Todas las demás» es la fila que arregla la socrática universal.** Una
explicación directa, un ejemplo trabajado, un primer paso ante bloqueo, una
aclaración o un desarrollo **no llevan repertorio de preguntas**, y no porque
falte contenido: porque inyectar un repertorio de preguntas junto a una
instrucción de explicar produce una respuesta que pregunta. Eso ya se midió en
este proyecto —`PM-B06`: *«lo concreto vence a lo abstracto»*, el modelo copió
el ejemplo del prompt palabra por palabra— y `D-20` lo volvió a ver con el
nivel 3.

Por eso el nivel 3 ya **no necesita una excepción**: `DESARROLLO_GUIADO` es una
estrategia que no está en la tabla de arriba, así que no recibe repertorio por
el mismo camino que las demás. `D-20` sigue siendo cierto; deja de ser un caso
especial.

El tono va aparte, y sigue sumando
-------------------------------------
Las dos plantillas afectivas —`P-AUTOCONCEPTO` y `P-AUTORREGULACION`— no
compiten con el repertorio principal: lo acompañan. Y ahora no las elige una
señal directamente, sino los **modificadores** que la política produjo a partir
de `nivel_intervencion`, que es lo que hace que ese nivel tenga efecto
comprobable. `p-retroalimentacion-autoconcepto.md` §Lo que esta plantilla no
hace lo exige: *«va JUNTO al contenido del turno, nunca en su lugar»*.


"""

from __future__ import annotations

from dataclasses import dataclass, field

from dominio.pedagogia import estrategias as E
from dominio.puertos.plantillas import (
    AUTOCONCEPTO,
    AUTORREGULACION,
    SCAFFOLDING_KQ,
    SOCRATICA_APOS,
    Plantilla,
    PuertoPlantillas,
)

#: Qué repertorio principal pide cada estrategia. Las que no están aquí **no
#: llevan ninguno**, y ésa es la fila que importa — ver la cabecera.
_REPERTORIO_DE_LA_ESTRATEGIA = {
    E.DIALOGO_SOCRATICO_APOS: SOCRATICA_APOS,
    E.SCAFFOLDING_KQ: SCAFFOLDING_KQ,
    E.CONFLICTO_CONCEPTUAL: SCAFFOLDING_KQ,
}

#: Las estrategias que trabajan sobre **una concepción concreta**: si la hay y
#: tiene secuencia escrita, esa secuencia gana a la plantilla genérica.
_USAN_LA_SECUENCIA = frozenset({E.SCAFFOLDING_KQ, E.CONFLICTO_CONCEPTUAL})

#: Qué plantilla de tono trae cada modificador. Es lo que convierte
#: `nivel_intervencion` en un efecto que se puede ver en el prompt.
_TONO_DEL_MODIFICADOR = {
    E.TONO_NO_EVALUATIVO: AUTOCONCEPTO,
    E.AUTORREGULACION: AUTORREGULACION,
}


@dataclass(frozen=True)
class Andamiaje:
    """Lo que este turno va a usar de `contenido/plantillas/`.

    `principal` es el repertorio del contenido matemático; `tono` son las
    plantillas afectivas que lo acompañan, y van aparte precisamente para que
    no puedan sustituirlo.
    """

    principal: Plantilla | None = None
    tono: tuple[Plantilla, ...] = ()
    #: Por qué se eligió eso, para la traza. `RF-REG-06` pide poder
    #: reconstruir la decisión pedagógica, no solo su resultado.
    motivo: str = ""
    concepcion: str = ""
    tonos_omitidos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def utilizable(self) -> bool:
        return (self.principal is not None and self.principal.utilizable) or bool(self.tono)


def elegir(
    plantillas: PuertoPlantillas | None,
    *,
    estrategia: str,
    modificadores: tuple[str, ...] = (),
    concepcion: str = "",
    concepciones_candidatas: tuple[str, ...] = (),
) -> Andamiaje:
    """El contenido de este turno, según la estrategia que la política eligió.

    `plantillas` puede ser `None` —sin adaptador de contenido— y entonces no
    hay andamiaje: el turno sigue con el andamio genérico del filtro 7, que es
    lo que hacía antes de `PM-B06`. Nunca lanza.

    `concepcion` es la **diagnosticada** cuando la hay; `concepciones_candidatas`
    son las que el motor simbólico conjeturó mirando la forma de la expresión.
    La primera gana a las segundas por la misma razón de siempre: el diagnóstico
    sale de lo que el estudiante eligió, la conjetura de cómo escribió.
    """
    if plantillas is None:
        return Andamiaje(motivo="sin adaptador de plantillas")

    principal, motivo, usada = _principal(
        plantillas, estrategia, concepcion, concepciones_candidatas
    )
    tono, omitidos = _tono(plantillas, modificadores)
    return Andamiaje(
        principal=principal,
        tono=tono,
        motivo=motivo,
        concepcion=usada,
        tonos_omitidos=omitidos,
    )


def _principal(
    plantillas: PuertoPlantillas,
    estrategia: str,
    concepcion: str,
    candidatas: tuple[str, ...],
) -> tuple[Plantilla | None, str, str]:
    """El repertorio principal, o ninguno. Ver la tabla de la cabecera."""
    clave = _REPERTORIO_DE_LA_ESTRATEGIA.get(estrategia)
    if clave is None:
        return (
            None,
            f"la estrategia «{estrategia}» no lleva repertorio de preguntas: "
            "inyectarlo produciría una respuesta que pregunta",
            "",
        )

    if estrategia in _USAN_LA_SECUENCIA:
        # La diagnosticada primero, y las candidatas después: preferir la
        # conjetura del motor sobre la elección del estudiante sería preferir la
        # conjetura al dato.
        for cual, procedencia in [(concepcion, "diagnosticada")] + [
            (c, "candidata") for c in candidatas
        ]:
            if not cual:
                continue
            secuencia = plantillas.secuencia_de(cual)
            if secuencia is not None and secuencia.utilizable:
                return secuencia, f"secuencia de la concepción {procedencia} {cual}", cual

    generica = plantillas.plantilla(clave)
    cual = concepcion or (candidatas[0] if candidatas else "")
    if cual:
        return (
            generica,
            f"la concepción «{cual}» no tiene secuencia escrita: repertorio genérico",
            cual,
        )
    return generica, f"repertorio de «{estrategia}»", ""


def _tono(
    plantillas: PuertoPlantillas, modificadores: tuple[str, ...]
) -> tuple[tuple[Plantilla, ...], tuple[str, ...]]:
    """Las afectivas que los modificadores piden. SUMAN, no sustituyen.

    Un modificador sin plantilla escrita se anota en `tonos_omitidos` en vez de
    desaparecer: `p-retroalimentacion-autoconcepto.md` §Cómo se eligen dice que
    *«si ninguna encaja con lo que de verdad pasó, no se emite ninguna»*, y
    saber que se quiso emitir una y no había es distinto de no haberla querido.
    """
    elegidas: list[Plantilla] = []
    omitidas: list[str] = []
    for modificador in modificadores:
        clave = _TONO_DEL_MODIFICADOR.get(modificador)
        if clave is None:
            continue
        plantilla = plantillas.plantilla(clave)
        if plantilla is not None and plantilla.utilizable:
            if plantilla not in elegidas:
                elegidas.append(plantilla)
        else:
            omitidas.append(clave)
    return tuple(elegidas), tuple(dict.fromkeys(omitidas))
