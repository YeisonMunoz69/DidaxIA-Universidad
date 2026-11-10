"""
redecision.py — Cuándo una decisión CONJUNTA es una decisión nueva (`D1B` bis)
===============================================================================

La política que faltaba, y el defecto que la hizo falta
----------------------------------------------------------------
`D1B` validaba cada dimensión de la decisión conjunta contra **su propia** tabla
de transiciones —`TRANSICIONES` para el titular, `TRANSICIONES_ASENTIMIENTO`
para el asentimiento—. Esas tablas responden una pregunta distinta de la que
aquí hace falta: *«¿puede este acto seguir al anterior cuando alguien mueve esta
dimensión sola?»*. Ahí, repetir `otorgado` es un doble clic y hay que
rechazarlo; de eso depende que revocar signifique algo.

Pero una decisión conjunta **no mueve una dimensión: mueve el par**. Y el
resultado era una contradicción alcanzable con dos gestos de rutas vigentes:

1. un menor acepta —`titular=otorgado`, `asentimiento=otorgado`—;
2. revoca **sólo** su asentimiento, por su ruta independiente (`EQ-016`);
3. vuelve a pulsar «Acepto y continuar»;
4. el asentimiento admite `revocado → otorgado`… y el titular tropieza con
   `otorgado → otorgado`, que su tabla lee como un doble clic;
5. la transacción entera falla y la persona queda bloqueada **sin salida desde
   el recorrido**.

Lo mismo al revés, y lo mismo cuando el equipo publica una versión nueva de un
solo alcance: el otro no tiene motivo propio para moverse y tumba la pareja.

La regla, en una frase
-------------------------------
Dentro de una decisión conjunta, el acto de la dimensión que ya estaba otorgada
**no es una repetición aislada: es la reafirmación que acompaña al cambio de la
otra**. Lo que decide si hay decisión nueva es el estado del **par**, no el de
cada mitad.

⚠️ Y sólo cuando de verdad hay un par · corrección de la segunda revisión
--------------------------------------------------------------------------------
Un adulto tiene **una** dimensión. Allí no hay ninguna otra que acompañar, así
que la reafirmación no significa nada y la semántica correcta sigue siendo la
individual del titular: `revocado → otorgado` sí, `revocado → rechazado` no
—quien revocó ya no tiene ninguna autorización vigente que rechazar, y el efecto
que buscaría ya lo tiene—.

La primera versión de este módulo trataba «una dimensión revocada» igual en los
dos casos y ofrecía las dos acciones al adulto, convirtiendo
`revocado → rechazado` en una transición que `TRANSICIONES` no admite.

La distinción es por **número de dimensiones** y está escrita como tal:

| dimensiones | política |
|---|---|
| **una** | `transicion_admitida()`, la de siempre, **llamada y no copiada** |
| **dos** | la del par, con la reafirmación |

`TRANSICIONES` y `TRANSICIONES_ASENTIMIENTO` siguen sin tocarse. La rama
individual **llama** a la función del dominio en vez de reimplementarla: dos
redacciones de la misma regla son dos reglas en cuanto alguien corrige una.

Qué NO se afloja, y por qué está aquí y no en las tablas de siempre
------------------------------------------------------------------------------
Poner una excepción dentro de `TRANSICIONES` habría contaminado la revocación:
`exigir_transicion()` la usan también `AdaptadorEventosDeConsentimientoPostgres`
y `AdaptadorAsentimientoPostgres` para escribir un acto **individual**, y ahí
`otorgado → otorgado` tiene que seguir siendo un rechazo. Las dos tablas quedan
exactamente como estaban. Esto es una política **aparte**, con nombre, que sólo
consume el caso de uso de la decisión conjunta.

Y conserva las dos negativas que importan:

- **la repetición exacta se rechaza.** Si el par ya dice exactamente eso sobre
  las versiones que rigen ahora, no hay decisión nueva: cero actos. Es lo que
  para el doble clic y para la segunda de dos peticiones simultáneas.
- **`rechazado` no es un atajo para revocar.** Con el par otorgado y al día, el
  recorrido no está pidiendo nada; una negativa directa saltaría el diálogo, la
  ruta y la semántica de `EQ-022`, así que se rechaza y se orienta a revocar.

Una sola autoridad, dos consumidores
---------------------------------------------
La misma función la usan el adaptador —dentro de la transacción, con la persona
bloqueada, para decidir si escribe— y el borde —para publicar en el estado qué
acciones admite el recorrido—. El navegador **consume** ese resultado; no lo
recalcula. Dos redacciones de esta regla serían dos reglas en cuanto alguien
corrigiera una, y la del navegador sería la que la persona ve.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dominio.modelo.consentimiento import EstadoConsentimiento, transicion_admitida
from dominio.modelo.decision_conjunta import Decision
from dominio.puertos.almacen import TransicionInvalida
from dominio.puertos.decision_conjunta import DecisionYaVigente, RevocacionRequerida

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from dominio.modelo.consentimiento import Alcance
    from dominio.modelo.identidad import CategoriaDeEdad


@dataclass(frozen=True, slots=True)
class DimensionDecidible:
    """Lo que hay hoy en una dimensión, ya leído de donde toque.

    Es un dato plano a propósito: lo construye el adaptador desde el cursor —con
    la fila de la persona bloqueada— y también el borde desde el `EstadoVigente`.
    Si este tipo supiera leer de algún sitio, sólo uno de los dos podría usarlo.

    `estado` llega como cadena porque las dos dimensiones tienen enumerados
    distintos —`EstadoConsentimiento` y `EstadoAsentimiento`— que comparten los
    valores que aquí importan. Traducir a un tercer enumerado habría añadido una
    tabla de equivalencias que mantener.

    Las dos categorías de edad son sólo del titular: `EQ-021` obliga a volver a
    pedir autorización cuando alguien cumple 18, y esa puerta se conserva. En el
    asentimiento van en `None` — quien deja de ser menor deja de tener esa
    dimensión, y eso lo decide quién aparece en la lista, no este campo.
    """

    alcance: Alcance
    estado: str
    version: str | None
    version_requerida: str | None
    categoria_del_acto: CategoriaDeEdad | None = None
    categoria_actual: CategoriaDeEdad | None = None

    def refleja(self, decision: Decision) -> bool:
        """Si esta dimensión **ya dice exactamente eso**, y sigue al día.

        Tres condiciones, y son las tres de `EQ-021` aplicadas a una dimensión:

        1. su último acto es esa decisión;
        2. lo es sobre la versión que rige **ahora** —una aceptación sobre un
           texto desplazado no dice nada sobre el que hoy se pide—;
        3. se emitió con la categoría de edad que la persona tiene hoy.

        Sin versión requerida publicada nunca refleja nada: no hay texto vigente
        contra el que comparar, así que la decisión sigue pendiente. Que además
        no se pueda registrar por falta de documento es otro desenlace y lo dice
        quien lee el catálogo.
        """
        if self.estado != decision.value:
            return False
        if self.version_requerida is None or self.version != self.version_requerida:
            return False
        return (
            self.categoria_del_acto is None
            or self.categoria_del_acto is self.categoria_actual
        )


@dataclass(frozen=True, slots=True)
class AccionesDeDecision:
    """Qué admite la política ahora mismo. Lo que el borde publica.

    ⚠️ **No dice si hay documento publicado.** Dice si la *política de
    redecisión* admite cada acción. Que exista un texto sobre el que decidir lo
    responde el catálogo de versiones, y la interfaz necesita las dos cosas: sin
    política no sabe si ofrecer las acciones, y sin versión no puede habilitarlas.
    """

    puede_aceptar: bool
    puede_rechazar: bool

    @property
    def requerida(self) -> bool:
        """Si el recorrido está pidiendo una decisión conjunta."""
        return self.puede_aceptar or self.puede_rechazar


def decision_conjunta_vigente(
    dimensiones: Iterable[DimensionDecidible],
) -> Decision | None:
    """La decisión que el par **entero** ya refleja, o `None`.

    `None` significa que no hay ninguna decisión conjunta coherente y al día: o
    falta decidir, o una dimensión se movió por su cuenta —una revocación
    independiente— o cambió alguna de las versiones requeridas. En los tres
    casos el recorrido está pidiendo una decisión nueva.

    Una lista **vacía** no refleja ninguna decisión: `all()` sobre vacío es
    cierto y devolvería la primera del enumerado, que sería afirmar que alguien
    decidió algo sin tener ni una dimensión que decidir.
    """
    candidatas = tuple(dimensiones)
    if not candidatas:
        return None
    for decision in Decision:
        if all(dimension.refleja(decision) for dimension in candidatas):
            return decision
    return None


def _admite_individual(dimension: DimensionDecidible, decision: Decision) -> bool:
    """Una sola dimensión: **la semántica de siempre**, llamada y no copiada.

    `transicion_admitida()` vive en `dominio/modelo/consentimiento.py` y ya
    responde exactamente esto, con las dos puertas de renovación de `EQ-021`
    —versión nueva y cambio de categoría de edad—. Reimplementarlo aquí habría
    dejado dos redacciones que divergen en cuanto alguien corrige una.

    El estado llega como cadena y los cuatro valores del titular coinciden con
    `EstadoConsentimiento`; un valor que no sea uno de ellos no es un estado de
    esta dimensión y no admite nada.

    ⚠️ **Sin versión requerida publicada, `cambia_version` sale cierto** y esto
    admite las dos acciones. Es deliberado: la política dice qué admitiría la
    *decisión*, y que además no haya documento sobre el que decidir lo responde
    el catálogo de versiones. El borde publica las dos cosas por separado y la
    interfaz las combina; fundirlas aquí habría hecho que «no hay texto» y «no
    hay nada que decidir» se presentaran igual, y se arreglan de formas
    distintas.
    """
    try:
        actual = EstadoConsentimiento(dimension.estado)
    except ValueError:
        return False
    return transicion_admitida(
        actual,
        EstadoConsentimiento(decision.value),
        cambia_version=dimension.version != dimension.version_requerida,
        cambia_categoria=(
            dimension.categoria_del_acto is not None
            and dimension.categoria_del_acto is not dimension.categoria_actual
        ),
    )


def _admite_conjunta(
    dimensiones: tuple[DimensionDecidible, ...], decision: Decision
) -> bool:
    """Dos dimensiones: la política del par, con la reafirmación."""
    vigente = decision_conjunta_vigente(dimensiones)
    if vigente is None:
        # El recorrido pide decidir: las dos acciones están sobre la mesa.
        return True
    if vigente is decision:
        # Exactamente lo mismo que ya está registrado.
        return False
    # Queda un solo caso: el par refleja la otra decisión. Cambiar un `rechazado`
    # por un `otorgado` es una decisión nueva y legítima; al revés sería retirar
    # una autorización vigente sin pasar por la revocación.
    return vigente is Decision.RECHAZADO


def admite_decision(
    dimensiones: Iterable[DimensionDecidible], decision: Decision
) -> bool:
    """Si esa decisión sería una decisión nueva y admisible.

    Se bifurca por el **número de dimensiones**, que es lo que distingue a un
    adulto de un menor sin que esta función tenga que saber nada de edades: quién
    aparece en la lista ya lo decidió quien la construyó.
    """
    candidatas = tuple(dimensiones)
    if not candidatas:
        return False
    if len(candidatas) == 1:
        return _admite_individual(candidatas[0], decision)
    return _admite_conjunta(candidatas, decision)


def acciones_disponibles(
    dimensiones: Iterable[DimensionDecidible],
) -> AccionesDeDecision:
    """Las dos acciones de la pantalla, resueltas por la misma política."""
    candidatas = tuple(dimensiones)
    return AccionesDeDecision(
        puede_aceptar=admite_decision(candidatas, Decision.OTORGADO),
        puede_rechazar=admite_decision(candidatas, Decision.RECHAZADO),
    )


def exigir_redecision(
    dimensiones: Iterable[DimensionDecidible], decision: Decision
) -> None:
    """`admite_decision()`, pero levantando el rechazo con su motivo.

    Se llama **una vez con el par completo**, dentro de la transacción y antes
    de insertar nada. Comprobarlo dimensión a dimensión es lo que producía el
    defecto: cada mitad tenía razón por separado y juntas se contradecían.

    Los rechazos son distintos y se le cuentan a la persona de formas distintas,
    así que son tipos y no un mensaje:

    - `DecisionYaVigente` · «esto ya está registrado, no hay nada que cambiar»;
    - `RevocacionRequerida` · «para retirar lo que autorizaste, revócalo»;
    - `TransicionInvalida` · el resto, que hoy es un único caso: rechazar cuando
      ya se revocó. No hay autorización que retirar ni decisión que repetir.
    """
    candidatas = tuple(dimensiones)
    if not candidatas:
        raise DecisionYaVigente(
            "no hay ninguna dimensión sobre la que decidir en esta decisión conjunta"
        )
    if admite_decision(candidatas, decision):
        return

    vigente = decision_conjunta_vigente(candidatas)
    if vigente is decision:
        raise DecisionYaVigente(
            f"esta decisión ya está registrada como {decision.value!r} sobre las "
            "versiones que rigen ahora: no hay nada nuevo que decidir"
        )
    if vigente is Decision.OTORGADO:
        raise RevocacionRequerida(
            "hay una autorización vigente y al día; para retirarla se revoca, no se "
            "rechaza: son dos actos con semántica distinta"
        )
    # Queda el caso que la corrección de la segunda revisión separó: una sola
    # dimensión que no refleja ninguna decisión —`revocado`— y aun así no admite
    # la que se pide. `revocado → rechazado` no es una transición de
    # `TRANSICIONES`, y no debe convertirse en una por pasar por aquí: quien
    # revocó ya no tiene ninguna autorización vigente que rechazar, y el efecto
    # que buscaría —quedar bloqueado— ya lo tiene.
    raise TransicionInvalida(
        f"no se puede pasar a {decision.value!r} desde el estado actual sin una "
        "decisión nueva que registrar"
    )
