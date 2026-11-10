"""
clasificador.py — El diagnóstico two-tier (S5 · `PM-B08` · `RF-DGC-01`, `RF-DGC-03`)
======================================================================================

`03-Plan-de-Construccion.md` incremento 4 declara **S5 entero ausente** en la
iteración 0: cuatro requisitos sin ningún código que los cubra. Este módulo es
`RF-DGC-01` —el patrón two-tier y su clasificación— y da la base con la que
`RF-DGC-03` se verifica sobre la regla de la cadena.

Por qué existe, y qué prerrequisito lo desbloqueó
------------------------------------------------------
`ADR-006` §3.3.bis documentó el motivo por el que esto se aplazaba: el grafo
del prototipo etiqueta sus aristas `misconception_asociada` con `M1`–`M5`,
pero el catálogo comprometido —y el contenido ya escrito, `p-two-tier.md`,
`c-m21.md`, `c-m22.md`— usa `M01`–`M24`. **Sin una correspondencia entre las
dos numeraciones, cualquier código que leyera una u otra podía estar leyendo
la incorrecta sin saberlo.** `D-13` (`OE2-Arquitectura/PM-V14-Correspondencia-
M1-M5.md`) cerró esa correspondencia: solo `M5`↔`M21` es aceptable, y las
demás no tienen equivalente. Este módulo la respeta por diseño: **nunca lee
`M1`–`M5`**, solo el catálogo `M01`–`M24` que el contenido ya usa —el mismo
que declara `dominio/arbitraje/divulgacion.py` para el resto del sistema—, así
que la ambigüedad que motivó el aplazamiento no puede colarse aquí.

La ruta diagnóstica del grafo que `ADR-006` §3.3 aplaza —enrutar la
recuperación cuando el estudiante **enuncia libremente** una concepción
errónea— **sigue aplazada** y no es lo que este módulo hace. Lo que aquí se
resuelve es la otra mitad de `S5`: un ítem **estructurado**, de dos turnos,
donde el estudiante no enuncia nada libremente — elige, y la elección ya
viene clasificada por quien escribió el contenido (`RC-PED-06`,
`p-two-tier.md`). Las dos rutas son independientes; solo comparten que ambas
hablan de "concepción errónea".

Qué produce, y qué no
--------------------------
`p-two-tier.md` §Los cuatro estados fija la parrilla 2×2 —`E1` comprensión,
`E2` acierto sin comprensión, `E3` error de ejecución, `E4` concepción
errónea— y qué sigue a cada uno. **Lo que ese documento no hace, y es
código, no contenido, según su propia sección final**: convertir el par
(respuesta, razón) en el estado. Eso es `clasificar()`.

Este módulo devuelve una **etiqueta de qué sigue** (`"avanzar"`,
`"sondeo_kq2"`, `"señalar_paso"`, `"remediar"`) y, si hay concepción, **su
identificador del catálogo** — nunca el texto pedagógico ni la plantilla
concreta (`s-m21.md`, `P-KQ1-KQ5`…), que es contenido y vive en
`contenido/plantillas/`. La misma frontera que ya separa `nivel_intervencion`
(`dominio/arbitraje/intervencion.py`, `PM-B13`) de la prosa que un día la
presentará.

Lo que queda fuera de esta sesión, y por qué
--------------------------------------------------
`RF-GPE-09` —re-evaluar el dominio de un nodo tras cada remediación— necesita
leer y escribir el registro conceptual `R-C` de `ADR-003` §6.2, que es
`PM-B09` y no existe todavía. `RF-DGC-10` —el sondeo inicial de
autopercepción— es una encuesta distinta, no el patrón two-tier, y
`03-Plan-de-Construccion.md` no lo exige para cerrar este incremento. Los dos
quedan **declarados, no resueltos**, igual que este módulo declara —no
inventa— la plantilla o secuencia que cada estado activa.
"""

from __future__ import annotations

from dataclasses import dataclass

#: La parrilla 2×2 de `p-two-tier.md` §Los cuatro estados.
COMPRENSION = "E1"
ACIERTO_SIN_COMPRENSION = "E2"
ERROR_DE_EJECUCION = "E3"
CONCEPCION_ERRONEA = "E4"

NOMBRE_ESTADO = {
    COMPRENSION: "comprensión",
    ACIERTO_SIN_COMPRENSION: "acierto sin comprensión",
    ERROR_DE_EJECUCION: "error de ejecución",
    CONCEPCION_ERRONEA: "concepción errónea",
}

#: Las cuatro etiquetas estructurales de «qué sigue». Son públicas porque
#: `dominio/pedagogia/andamiaje.py` las traduce a plantilla concreta y hasta el
#: 2026-08-12 las copiaba en vez de importarlas: dos listas que tienen que
#: coincidir son una que puede dejar de hacerlo.
AVANZAR = "avanzar"
SONDEO_KQ2 = "sondeo_kq2"
SEÑALAR_PASO = "señalar_paso"
REMEDIAR = "remediar"

#: Qué sigue a cada estado — la tabla «Qué sigue» de `p-two-tier.md`, en la
#: etiqueta estructural que el contenido resuelve a plantilla concreta.
_SIGUIENTE = {
    COMPRENSION: AVANZAR,
    ACIERTO_SIN_COMPRENSION: SONDEO_KQ2,
    ERROR_DE_EJECUCION: SEÑALAR_PASO,
    CONCEPCION_ERRONEA: REMEDIAR,
}


@dataclass(frozen=True)
class OpcionRazon:
    """Una de las opciones del turno 2, tal como el contenido la escribió.

    `concepcion` usa siempre el catálogo `M01`–`M24` —nunca `M1`–`M5` del
    grafo, ver el docstring del módulo—. `None` cuando la opción es la razón
    correcta, o cuando el contenido no llegó a tipificarla (se declara en
    `Diagnostico.motivo`, no se inventa una).

    ⚠️ **`texto` es lo ÚNICO de este tipo que puede cruzar al estudiante**, y
    se añadió el 2026-08-14 con `PM-B28`, cuando apareció quien muestra el
    ítem. `es_correcta` y `concepcion` **nunca** cruzan: emitirlos resolvería
    el ítem antes de plantearlo. Quien traduce al contrato es
    `adaptadores/entrantes/http/turno.py`, y ahí está la prueba que lo fija.
    """

    identificador: str
    es_correcta: bool
    concepcion: str | None = None
    #: La razón tal como el contenido la escribió, para enseñársela. Vacía si
    #: el banco no la trajo: el ítem sigue siendo clasificable —`clasificar()`
    #: no lee esto— pero no ofrecible, que son dos cosas distintas.
    texto: str = ""


@dataclass(frozen=True)
class RespuestaAlItem:
    """Lo que el estudiante dejó en el ítem, **sin evaluar todavía**.

    Es la forma cruda: el resultado tal como lo escribió y **cuál** de las
    opciones eligió, por su identificador. Ni el resultado está comprobado ni
    la opción está resuelta contra el banco — las dos cosas las hace
    `dominio/filtros/diagnostico.py` con el puerto simbólico y el puerto de
    plantillas, y de ahí sale la `RespuestaDosNiveles` de abajo.

    **Existe para que el borde no tenga que evaluar nada.** Si `es_correcta` o
    `concepcion` viajaran desde el cliente, el estudiante podría diagnosticarse
    a sí mismo escribiendo un campo, que es la misma razón por la que `Señales`
    no viaja desde el navegador (ver `adaptadores/entrantes/http/turno.py`).
    """

    nodo: str
    resultado: str
    razon: str


@dataclass(frozen=True)
class RespuestaDosNiveles:
    """Lo que el estudiante dejó en los dos turnos del ítem, ya evaluado.

    `respuesta_correcta` la decide quien verificó el turno 1 —para cálculo
    diferencial, `AdaptadorSimbolico`, el mismo motor que ya verifica el resto
    del sistema; `RC-PED-06` no pide un verificador aparte—. `opcion` es la
    que el estudiante eligió en el turno 2, ya resuelta contra el banco del
    ítem: este módulo no interpreta texto libre.
    """

    nodo: str
    respuesta_correcta: bool
    opcion: OpcionRazon


@dataclass(frozen=True)
class Diagnostico:
    """El estado de `p-two-tier.md`, con qué sigue y por qué.

    `RF-DGC-03`: cada estado tiene que producir una selección de remediación
    **distinta y verificable** — `siguiente` es esa selección, a nivel
    estructural; `concepcion` la distingue todavía más dentro de `E4`, que es
    donde `RC-PED-06` exige que cada opción delate una concepción concreta y
    no otra."""

    estado: str
    nodo: str
    siguiente: str
    concepcion: str | None = None
    motivo: str = ""

    @property
    def nombre(self) -> str:
        return NOMBRE_ESTADO[self.estado]


def clasificar(respuesta: RespuestaDosNiveles) -> Diagnostico:
    """El estado two-tier de este ítem, tal como `p-two-tier.md` lo define.

    La regla es la parrilla 2×2, literal: el estado no depende de la
    magnitud de nada —igual que `T6`, `ADR-003` C2— sino de dos booleanos.
    """
    if respuesta.respuesta_correcta and respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=COMPRENSION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[COMPRENSION],
            motivo="resultado correcto y razón correcta",
        )
    if respuesta.respuesta_correcta and not respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=ACIERTO_SIN_COMPRENSION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[ACIERTO_SIN_COMPRENSION],
            concepcion=respuesta.opcion.concepcion,
            motivo="resultado correcto con razón incorrecta: el estado que "
            "un ítem de un solo nivel no puede ver",
        )
    if not respuesta.respuesta_correcta and respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=ERROR_DE_EJECUCION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[ERROR_DE_EJECUCION],
            motivo="resultado incorrecto con razón correcta: sabe lo que "
            "hace y se equivocó al hacerlo, no hay concepción que remediar",
        )
    # resultado incorrecto y razón incorrecta · E4
    if respuesta.opcion.concepcion is None:
        motivo = (
            "resultado y razón incorrectos, pero la opción elegida no llegó "
            "tipificada con una concepción — se declara, no se inventa una"
        )
    else:
        motivo = f"resultado y razón incorrectos: delata {respuesta.opcion.concepcion}"
    return Diagnostico(
        estado=CONCEPCION_ERRONEA,
        nodo=respuesta.nodo,
        siguiente=_SIGUIENTE[CONCEPCION_ERRONEA],
        concepcion=respuesta.opcion.concepcion,
        motivo=motivo,
    )
