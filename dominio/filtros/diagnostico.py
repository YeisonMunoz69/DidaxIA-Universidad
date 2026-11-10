"""
diagnostico.py — Filtro 6.75 · el diagnóstico two-tier corre en el turno
==============================================================================

`dominio/diagnostico/clasificador.py` (`PM-B08`, `RF-DGC-01`) se escribió el
2026-08-12, pasó sus ocho pruebas, se marcó cerrado — y **nadie lo llamaba**.
`dominio/pedagogia/andamiaje.py` aceptaba su etiqueta desde el día siguiente y
la recibía siempre vacía. Este filtro es lo que faltaba entre las dos puntas.

Es la cuarta vez que este proyecto encuentra el mismo patrón en dos días —el
filtro 3, el filtro 12, las plantillas y esto—, y la lección está escrita en
`CONTEXTO-MAESTRO.md` §8.octies: *«una casilla marcada y una prueba en verde no
significan que el sistema lo haga»*.

Por qué va aquí y no en los otros dos sitios posibles
--------------------------------------------------------------
El encargo dejaba abierto dónde poner el cálculo. Va **inmediatamente antes del
filtro 7**, y las tres alternativas se descartaron por motivos distintos:

| Dónde | Por qué no |
|---|---|
| Dentro del filtro 3 | El 3 es el modelo **afectivo** (`ADR-003`): ansiedad, autoeficacia. Esto es el modelo **conceptual** (`S5`). Fundirlos pondría dos modelos del estudiante en un archivo, y además el 3 corre antes de que exista `nodo_activo` |
| Dentro del filtro 6.5 | El 6.5 tiene una responsabilidad —*«el desarrollo llega al generador ya hecho»*— y **solo corre si la intención es procedimental**. Un ítem de dos niveles se contesta también en un turno que no lo es |
| Entre el 4 y el 5 | Ahí el diagnóstico **cambiaría lo que se recupera**, y enrutar la recuperación por la concepción detectada es justo la *ruta diagnóstica del grafo* que `ADR-006` §3.3 tiene **aplazada**. Abrirla por la puerta de atrás sería tomar esa decisión sin tomarla |

Lo que queda, y es el criterio que se sigue: **el único consumidor del
diagnóstico es el filtro 7**, así que va lo más tarde posible. Colocado ahí no
puede cambiar en silencio nada de lo que ya hacían la recuperación, el
arbitraje ni el precómputo — todos ven exactamente lo que veían antes.

En qué casos SÍ se diagnostica y en cuáles no · lo que el encargo pedía dejar escrito
--------------------------------------------------------------------------------------
**Sí**, y hacen falta las cuatro cosas a la vez:

1. El turno **responde a un ítem de dos niveles** (`ctx.respuesta_al_item`).
2. Ese nodo **tiene ítem escrito** con sus razones tipificadas — hoy solo
   `N08`; `N14` y `N05` están declarados en `p-two-tier.md` y sin escribir.
3. La razón elegida **es una del ítem**.
4. El motor simbólico **pudo corregir el turno 1**.

**No**, y entonces `ctx.diagnostico` queda `None` con el motivo en la traza:
en un turno de texto libre —que son todos los de hoy—, y en cada uno de los
cuatro fallos de arriba.

⚠️ **Y en un turno de texto libre no se fabrica un diagnóstico plausible.** Se
podría: hay una respuesta del estudiante y hay
`precomputo.concepciones_candidatas`. Pero la parrilla 2×2 necesita **la razón**,
y `p-two-tier.md` existe precisamente porque *«una respuesta correcta no prueba
comprensión y una incorrecta no prueba su ausencia»*. Derivar el estado del
resultado solo reproduciría el ítem de un nivel que esa plantilla rechaza, y
además `R-09` recuerda que ninguna taxonomía de concepciones se validó en
diálogo espontáneo. Un `None` honesto vale más que un `E4` inventado.

La distinción que no se puede perder: fallar ≠ no poder comprobar
--------------------------------------------------------------------------
`ADR-008` V1 dice que sin verificación **no hay aprobación**, y para el filtro 9
eso es correcto: una afirmación que no se pudo comprobar no se emite como
comprobada. Aquí sería un error traducirlo igual. Si el motor no pudo leer lo
que el estudiante escribió, eso **no** es «el estudiante se equivocó»: es que no
lo sabemos, y un `E4` sacado de ahí acusaría de una concepción errónea a quien
solo escribió raro. Por eso `NO_VERIFICABLE` deja el diagnóstico vacío y no lo
convierte en `respuesta_correcta=False`.


"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol, runtime_checkable

from dominio.diagnostico.clasificador import (
    Diagnostico,
    RespuestaDosNiveles,
    clasificar,
)
from dominio.filtros.base import Filtro
from dominio.modelo.matematica import BloqueVerificable, InformeVerificacion, Veredicto
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.sondeo import Desenlace, DesenlaceDelSondeo, validar_respuesta
from dominio.puertos.plantillas import ItemDosNiveles, PuertoPlantillas


@runtime_checkable
class _PuertoDeCorreccion(Protocol):
    """Lo único de `PuertoSimbolico` que este filtro necesita.

    Declarado aparte —igual que hace el filtro 6.5 con `precomputar`— porque
    este filtro no precomputa nada: darle el puerto entero le daría una
    capacidad que no le toca ejercer.
    """

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion: ...


class FiltroDiagnostico(Filtro):
    """Filtro 6.75 · `RF-DGC-01` corriendo en la cadena de `ADR-001` §6.3.

    Los dos puertos son opcionales y por inyección, igual que el andamiaje del
    filtro 7: sin `contenido/plantillas/` no hay ítem que reconocer, y el turno
    sigue exactamente como iba. Que falte el diagnóstico degrada la elección
    pedagógica; no rompe nada.
    """

    nombre = "diagnóstico conceptual de dos niveles"
    ruta = "caliente"

    def __init__(
        self,
        plantillas: PuertoPlantillas | None = None,
        simbolico: _PuertoDeCorreccion | None = None,
    ) -> None:
        self._plantillas = plantillas
        self._simbolico = simbolico

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        diagnostico, desenlace = self._diagnosticar(ctx)
        if diagnostico is None:
            return replace(ctx, desenlace_del_sondeo=desenlace), {
                "diagnosticado": False,
                "motivo": desenlace.motivo,
                # `R2-B` · el desenlace va a la traza porque es lo que gobierna
                # las mutaciones de sesión de este turno. Sin él, «no se
                # diagnosticó» no distingue un payload rechazado de una
                # respuesta legítima que el motor no pudo corregir, y las dos
                # dejan el sistema en un estado distinto.
                "desenlace": desenlace.estado.value,
            }

        meta = {
            "diagnosticado": True,
            "estado": diagnostico.estado,
            "nombre": diagnostico.nombre,
            "nodo": diagnostico.nodo,
            "siguiente": diagnostico.siguiente,
            "concepcion": diagnostico.concepcion or "",
            # `RF-REG-06` pide reconstruir la decisión, no solo su resultado:
            # el filtro 12 se lleva esto al registro del turno.
            "motivo": diagnostico.motivo,
            "desenlace": desenlace.estado.value,
        }
        return replace(
            ctx, diagnostico=diagnostico, desenlace_del_sondeo=desenlace
        ), meta

    def _diagnosticar(
        self, ctx: ContextoTurno
    ) -> tuple[Diagnostico | None, DesenlaceDelSondeo]:
        """El estado de este turno y **en qué acabó la respuesta al ítem**.

        Las cuatro condiciones de la cabecera, en orden y cada una con su
        motivo propio: un solo «no se pudo» las escondería todas.

        🔴 `R2-B` · devuelve además un `DesenlaceDelSondeo`, y esa segunda mitad
        es la corrección. Este filtro es el **único** sitio del sistema que
        valida la respuesta contra el banco y contra lo que la sesión ofreció,
        así que es el único que puede decir si se admitió. Antes no lo decía a
        nadie, y el borde HTTP acababa infiriéndolo de que el cliente había
        mandado el campo. Ver `DesenlaceDelSondeo`.
        """
        cruda = ctx.respuesta_al_item
        if cruda is None:
            return None, DesenlaceDelSondeo(
                estado=Desenlace.SIN_RESPUESTA,
                motivo="el turno no responde a un ítem de dos niveles",
            )
        if self._plantillas is None:
            # No es un rechazo: es el servidor sin banco. Un ítem que no se
            # puede consultar no se contesta ni se cierra.
            return None, DesenlaceDelSondeo(
                estado=Desenlace.NO_CLASIFICABLE,
                nodo=cruda.nodo,
                motivo="sin puerto de plantillas: no hay banco de ítems que consultar",
            )

        item = self._plantillas.item_de(cruda.nodo)
        # 🔴 Fase 4 · **se valida antes de clasificar**, y la comprobación que
        # faltaba es que el ítem se hubiera ofrecido en ESTA sesión. Ver
        # `dominio/pedagogia/sondeo.py::validar_respuesta`.
        veredicto = validar_respuesta(
            cruda, item, ctx.sondeos_ofrecidos, ctx.sondeos_contestados
        )
        if not veredicto.admitida:
            return None, DesenlaceDelSondeo(
                estado=Desenlace.RECHAZADA, nodo=cruda.nodo, motivo=veredicto.motivo
            )

        opcion = item.opcion(cruda.razon)
        correcta = self._turno_1_correcto(item, cruda.resultado)
        if correcta is None:
            # Admitida pero no clasificable. El ítem **no** se cierra: sin
            # diagnóstico, cerrarlo le quitaría al estudiante su única
            # oportunidad sobre esas cuatro razones a cambio de nada.
            return None, DesenlaceDelSondeo(
                estado=Desenlace.NO_CLASIFICABLE,
                nodo=item.nodo,
                motivo="no se pudo comprobar el resultado del turno 1",
            )

        return clasificar(
            RespuestaDosNiveles(
                nodo=item.nodo, respuesta_correcta=correcta, opcion=opcion
            )
        ), DesenlaceDelSondeo(
            estado=Desenlace.PROCESADA,
            nodo=item.nodo,
            motivo="la respuesta se admitió y se clasificó",
        )

    def _turno_1_correcto(self, item: ItemDosNiveles, resultado: str) -> bool | None:
        """Si lo que el estudiante escribió es la derivada del ítem.

        `None` cuando no se pudo comprobar, que **no es lo mismo que falso** —
        ver la cabecera. Se usa `verificar()` y no `precomputar()` porque la
        pregunta es de equivalencia y no de desarrollo: `d/dx <ítem> = <lo que
        escribió>` es exactamente el bloque que el filtro 9 ya sabe juzgar, y
        pedirle al motor una segunda forma de comparar sería tener dos que
        pueden discrepar.
        """
        if self._simbolico is None or not resultado.strip():
            return None
        try:
            informe = self._simbolico.verificar(
                [
                    BloqueVerificable(
                        identificador="turno-1",
                        izquierda=f"d/dx ({item.derivar})",
                        derecha=resultado.strip(),
                        relacion="=",
                    )
                ]
            )
        except Exception:  # noqa: BLE001 — corregir no puede tumbar el turno
            return None

        if not informe.verificaciones:
            return None
        veredicto = informe.verificaciones[0].veredicto
        if veredicto is Veredicto.NO_VERIFICABLE:
            return None
        return veredicto is Veredicto.VALIDA
