"""
decision_conjunta.py — Los actos que produce UNA decisión visible (`D0` §10.10)
================================================================================

`D0` §10.10 decide una sola acción, «Acepto y continuar», y **actos separados**:

    «Para un adulto, la acción crea un evento `titular`; para un menor crea
    atómicamente un evento `titular` y otro de `asentimiento`, cada uno con su
    propio recibo.»

Este módulo es el tipo de ese resultado. No es un evento fundido y no es un
alcance nuevo: es la **lista** de los actos que quedaron escritos, en el orden
en que se escribieron, con la secuencia y el momento reales de cada fila.

Por qué un tipo y no una tupla de eventos
---------------------------------------------
Porque el orden es contrato —titular primero, asentimiento después— y la
cardinalidad también: uno para el adulto, dos para el menor, nunca otra cosa.
Una tupla suelta lo habría dejado en manos de quien la construyera, y el borde
habría tenido que volver a comprobarlo para poder confiar en `recibos[0]`.

Aquí se comprueba una vez, al construir, y por eso un adaptador que devolviera
el asentimiento primero —o dos titulares— falla **antes** de que nadie serialice
un recibo equivocado.

Las cuatro secciones NO están aquí, y es deliberado
-------------------------------------------------------------
La política de privacidad, las condiciones, la participación en la investigación
y la medición conductual son **secciones del paquete versionado del titular**
(`D0` §10.10), no cuatro alcances ni cuatro finalidades. Su unidad de verdad es
la `huella_contenido` de la versión `titular`, que representa el paquete
canónico completo que la persona leyó. Modelarlas como valores aquí las habría
convertido en cuatro cosas que el sistema puede conceder por separado, que es
exactamente lo que la decisión descarta.

Las seis finalidades cerradas y los tres alcances siguen siendo los de
`dominio/modelo/consentimiento.py`, sin añadir ni quitar ninguno.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.menores import EstadoAsentimiento


class DecisionInvalida(ValueError):
    """Un valor que no puede formar parte de una decisión ni de sus actos."""


class Decision(StrEnum):
    """Lo único que el cliente decide: aceptar o no aceptar.

    Dos valores y no cuatro. `revocado` no está —`EQ-022` le da su propia ruta,
    su propia regla de versión y su propia semántica— y `pendiente` no es un
    acto: es la ausencia de todos ellos.
    """

    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"

    @property
    def como_consentimiento(self) -> EstadoConsentimiento:
        """El estado equivalente en la dimensión del titular."""
        return EstadoConsentimiento(self.value)

    @property
    def como_asentimiento(self) -> EstadoAsentimiento:
        """El estado equivalente en la dimensión del menor."""
        return EstadoAsentimiento(self.value)


def decision_desde(valor: object) -> Decision | None:
    """La decisión que nombra `valor`, o `None` si no nombra ninguna.

    Estricta a propósito: no recorta espacios y no normaliza mayúsculas.
    `"Otorgado"` y `" otorgado "` no son la decisión —son un cliente que manda
    otra cosa— y aceptarlos habría convertido esta frontera en una que adivina.
    """
    if not isinstance(valor, str):
        return None
    try:
        return Decision(valor)
    except ValueError:
        return None


#: El orden en que los actos de una decisión se escriben y se devuelven.
#:
#: `D0` §10.10 lo fija —titular primero, asentimiento después— y el encargo de
#: `D1B` lo repite: «el orden de los recibos será titular y luego asentimiento».
#: Vive como constante para que el adaptador, el borde y las pruebas lo lean del
#: mismo sitio en vez de repetir dos literales que podrían desordenarse.
ORDEN_DE_LOS_ACTOS: tuple[Alcance, ...] = (Alcance.TITULAR, Alcance.ASENTIMIENTO)


@dataclass(frozen=True, slots=True)
class ActoRegistrado:
    """Una fila que ya está en la base, con lo que la identifica.

    Los seis campos del recibo del hito R3 —secuencia, momento, versión,
    alcance, decisión y huella—, y ninguno más. No lleva el sujeto: quien recibe
    esto acaba de decidir sobre sí mismo, y arrastrar el identificador de la
    persona por la respuesta lo pondría en un sitio donde no hace falta.

    `secuencia` es el `id` que asignó PostgreSQL. Vale siempre más que cero: un
    acto sin secuencia no está persistido, y este tipo describe lo que sí lo
    está.
    """

    alcance: Alcance
    version: str
    decision: Decision
    comprobante: str
    momento: datetime
    secuencia: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        object.__setattr__(self, "decision", Decision(self.decision))
        if not isinstance(self.version, str) or not self.version.strip():
            raise DecisionInvalida("un acto registrado tiene que nombrar su versión")
        if not isinstance(self.comprobante, str) or not SHA256.fullmatch(self.comprobante):
            raise DecisionInvalida("el comprobante tiene que ser un SHA-256 en minúsculas")
        if not isinstance(self.momento, datetime):
            raise DecisionInvalida("momento tiene que ser la fecha que asignó el almacén")
        if isinstance(self.secuencia, bool) or not isinstance(self.secuencia, int):
            raise DecisionInvalida("la secuencia es el identificador que asignó el almacén")
        if self.secuencia <= 0:
            raise DecisionInvalida("un acto sin secuencia no está persistido")


@dataclass(frozen=True, slots=True)
class ActosDeLaDecision:
    """Lo que UNA decisión dejó escrito, entero y en orden.

    Las tres reglas que se comprueban aquí y no en el borde:

    1. **hay al menos un acto** — una decisión que no escribió nada no es una
       decisión registrada, y devolverla como éxito sería el éxito parcial que
       `EQ-024` prohíbe;
    2. **el primero es el titular** — el borde publica `recibos[0]` como el
       recibo del titular y tiene que poder confiar en ello;
    3. **no se repite un alcance y no aparece uno de fuera de `D0` §10.10** — la
       autorización del representante conserva su alcance, su evidencia y su
       revisión separados, y no la produce esta acción.

    Todos los actos comparten decisión: una sola acción visible no puede otorgar
    en una dimensión y rechazar en la otra. Un rechazo del menor registra su
    rechazo de las dos dimensiones aplicables, que es lo que el encargo pide.
    """

    sujeto_google: str
    actos: tuple[ActoRegistrado, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.sujeto_google, str) or not self.sujeto_google.strip():
            raise DecisionInvalida("los actos pertenecen a un sujeto y hay que decir cuál")
        actos = tuple(self.actos)
        if not actos:
            raise DecisionInvalida("una decisión registrada tiene al menos un acto")
        alcances = tuple(a.alcance for a in actos)
        if alcances != ORDEN_DE_LOS_ACTOS[: len(alcances)]:
            raise DecisionInvalida(
                "los actos de una decisión van en el orden "
                f"{[a.value for a in ORDEN_DE_LOS_ACTOS]} y llegaron "
                f"{[a.value for a in alcances]}"
            )
        if len({a.decision for a in actos}) != 1:
            raise DecisionInvalida(
                "una sola acción visible no puede otorgar en una dimensión y "
                "rechazar en la otra"
            )
        object.__setattr__(self, "actos", actos)

    @property
    def decision(self) -> Decision:
        """La decisión única que produjo todos estos actos."""
        return self.actos[0].decision

    @property
    def titular(self) -> ActoRegistrado:
        """El acto del titular, que siempre existe."""
        return self.actos[0]

    @property
    def incluye_asentimiento(self) -> bool:
        """Si la persona era menor y por tanto se escribieron dos actos."""
        return len(self.actos) > 1
