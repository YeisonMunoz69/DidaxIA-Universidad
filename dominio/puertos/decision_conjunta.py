"""
decision_conjunta.py — Una decisión, todos sus actos, una transacción (`D1B`)
==============================================================================

La frontera que `D0` §10.10 exige y que hasta hoy no existía:

    «El servidor debe resolver las versiones vigentes y guardar **atómicamente**
    los actos independientes que correspondan […]; no se resuelve con dos
    peticiones encadenadas desde Svelte.»

Un método, dos parámetros, y ésa es la mitad del contrato
------------------------------------------------------------
`registrar_decision(sujeto_google, decision)`. Nada más entra. **Ni edad, ni
versión, ni alcance, ni huella, ni comprobante**, y no es una omisión que se
pueda añadir después sin que se note: cada uno de esos cinco valores gobierna
una regla que el cliente no puede decidir.

- la **edad** decide el régimen entero de `EQ-016` —cuántos actos se escriben— y
  se lee de `persona` con la fila bloqueada;
- la **versión** decide qué se aceptó; dejarla elegir permitiría aceptar un
  texto ya desplazado, que es el fallo que el hito A2 corrigió;
- el **alcance** decide en qué tabla cae el acto;
- la **huella** es la prueba de qué texto se leyó;
- el **comprobante** se calcula sobre los cuatro anteriores; uno que enviara el
  navegador probaría lo que el navegador quisiera.

Los cinco los resuelve la implementación **dentro** de la misma transacción, con
la persona bloqueada, de modo que ninguno pueda cambiar entre que se lee y que
se escribe.

Qué NO hace esta frontera
-----------------------------
- **No toca la autorización del representante.** `EQ-016` la declara una
  dimensión independiente, con su evidencia, su plazo y su revisión por un
  investigador autorizado (`EQ-023`). `D1B` no la funde con el botón.
- **No revoca.** `EQ-022` separa dos vigencias y le da a la revocación su propia
  ruta y su propia regla de versión —la de la concesión efectivamente otorgada,
  aunque su texto haya vencido—. Admitir `revocado` aquí habría hecho que
  aceptar y retirar compartieran validación.
- **No publica versiones.** Si falta la versión de cualquier alcance necesario,
  no se escribe **ningún** evento y se dice cuáles faltan.

Todo o nada, y qué significa exactamente
--------------------------------------------
Para un menor son dos INSERT en dos tablas. Si el segundo falla, el primero se
revierte: la implementación abre **una** conexión y **una** transacción, y no
compone dos adaptadores existentes uno detrás del otro. Dos adaptadores serían
dos transacciones, y entre ellas cabe un fallo que dejaría un consentimiento del
titular sin el asentimiento que lo acompaña —una persona con la mitad de su
decisión registrada y ninguna forma de saberlo—.

Y dos decisiones simultáneas del mismo sujeto no producen dos juegos de actos:
la fila de `persona` se bloquea con `FOR UPDATE`, la segunda espera, y al llegar
encuentra el estado que dejó la primera. Su transición ya no es válida y se
rechaza limpiamente.


"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dominio.puertos.almacen import EscrituraRechazada
from dominio.puertos.gobierno import SupresionEnCurso

#: Se reexporta para que quien la importaba por este módulo la siga
#: encontrando. **La definición vive en `dominio/puertos/gobierno.py`** desde la
#: corrección transversal: la regla es del gobierno de datos y no de esta
#: operación, y dos clases con el mismo significado serían dos reglas en cuanto
#: alguien corrigiera una.
__all__ = [
    "DecisionYaVigente",
    "PuertoDecisionConjunta",
    "RedecisionNoRequerida",
    "RevocacionRequerida",
    "SupresionEnCurso",
    "VersionesFaltantes",
]

if TYPE_CHECKING:  # pragma: no cover
    from dominio.modelo.consentimiento import Alcance
    from dominio.modelo.decision_conjunta import ActosDeLaDecision, Decision


class VersionesFaltantes(EscrituraRechazada):
    """No hay texto publicado en alguno de los alcances que hacían falta.

    No es un fallo del almacén ni un error del cliente: es el estado real de
    este árbol —el equipo todavía no ha aprobado ningún texto (`D0` §10.9)— y la
    respuesta honesta es decir **cuáles** faltan, no un rechazo genérico.

    `alcances` es una lista cerrada de valores de `Alcance`, en el orden en que
    los actos se habrían escrito. Quien la reciba puede nombrarlos uno a uno sin
    volver a preguntar.

    ⚠️ Cuando esto se levanta, **cero eventos quedan escritos**. La comprobación
    va antes que cualquier INSERT y, aunque no fuera así, la transacción entera
    se revierte.
    """

    def __init__(self, alcances: tuple[Alcance, ...]) -> None:
        self.alcances = tuple(alcances)
        nombres = ", ".join(f"«{a.value}»" for a in self.alcances)
        super().__init__(f"no hay ninguna versión vigente de: {nombres}")


class RedecisionNoRequerida(EscrituraRechazada):
    """El recorrido no esta pidiendo esta decision conjunta.

    Raiz comun de los dos rechazos que la politica de `dominio/modelo/redecision.py`
    produce. Se declara para que quien quiera tratarlos juntos —el borde, al
    traducirlos a un `409`— pueda hacerlo sin enumerarlos, y para que anadir un
    tercero no obligue a tocar cada `except`.

    Los dos que existen NO son intercambiables: uno dice «ya esta hecho» y el
    otro «esa no es la puerta». Se le cuentan a la persona de formas distintas.
    """


class DecisionYaVigente(RedecisionNoRequerida):
    """El par entero ya refleja exactamente esa decision, y al dia.

    Es el doble clic, la peticion duplicada y la segunda de dos simultaneas. No
    se escribe ningun acto: repetir una decision no la hace mas cierta, y crearia
    un evento que nadie tomo.
    """


class RevocacionRequerida(RedecisionNoRequerida):
    """Se pidio rechazar con una autorizacion vigente y al dia.

    `EQ-022` separa rechazar de revocar: revocar retira una concesion que se
    otorgo —con su ruta, su dialogo y su regla de version—, y rechazar es decidir
    que no se autoriza lo que hoy se pide. Con el par otorgado y al dia no hay
    nada pendiente que decidir, asi que admitir un rechazo aqui seria abrir una
    via alternativa a la revocacion que se salta su semantica entera.
    """


@runtime_checkable
class PuertoDecisionConjunta(Protocol):
    """Registrar de una vez todos los actos que una decisión produce."""

    def registrar_decision(
        self, sujeto_google: str, decision: Decision
    ) -> ActosDeLaDecision:
        """Escribe atómicamente los actos que le correspondan a esta persona.

        Un acto de alcance `titular` para un adulto; ése **y** uno de alcance
        `asentimiento` para un menor, los dos en la misma transacción. Otorgar y
        rechazar siguen la misma cardinalidad: un rechazo del menor registra su
        rechazo de las dos dimensiones aplicables.

        Devuelve los eventos **reales**, con la secuencia y el momento que
        asignó el almacén, en el orden en que se escribieron.

        Desenlaces, y ninguno se confunde con otro:

        - `ReferenciaDesconocida` · esa persona no está registrada;
        - `PerfilSinEdad` · existe y no ha declarado edad, así que no hay régimen
          de `EQ-016` que aplicar y el acto no se registra;
        - `VersionesFaltantes` · falta el texto de algún alcance necesario;
        - `SupresionEnCurso` · hay un trámite de supresión abierto y durante él
          no se trata nada nuevo;
        - `TransicionInvalida` · la decisión no puede seguir al estado vigente
          —un doble clic, o una decisión concurrente que llegó antes—;
        - `AlcanceIncorrecto` / `VersionNoVigente` · la versión resuelta dejó de
          servir entre que se leyó y que se escribió;
        - `AlmacenNoConfigurado` / `AlmacenNoDisponible` · no se sabe. Quien
          llama muestra mantenimiento (`EQ-024`) y **nunca** una aceptación
          aparente.

        En los seis primeros casos no queda ningún evento escrito.
        """
        ...
