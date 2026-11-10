from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from dominio.puertos.plantillas import ItemDosNiveles


_TURNOS_ENTRE_SONDEOS = 3


_INTENTOS_MINIMOS = 2


@dataclass(frozen=True)
class ItemOfrecido:

    nodo: str
    razones: tuple[str, ...] = ()

@dataclass(frozen=True)
class Veredicto:

    admitida: bool
    motivo: str = ""

def validar_respuesta(
    respuesta,
    item,
    ofrecidos: tuple[ItemOfrecido, ...],
    contestados: tuple[str, ...] = (),
) -> Veredicto:

    if item is None or not item.utilizable:
        return Veredicto(False, f"no hay ítem de dos niveles utilizable para «{respuesta.nodo}»")

    ofrecido = next((o for o in ofrecidos if o.nodo == item.nodo), None)
    if ofrecido is None:
        return Veredicto(
            False,
            f"el ítem de «{item.nodo}» no se planteó en esta sesión: no se clasifica",
        )
    if ofrecidos[-1].nodo != item.nodo:
        return Veredicto(
            False,
            f"el ítem de «{item.nodo}» ya no es el vigente: la sesión ofreció "
            f"después el de «{ofrecidos[-1].nodo}»",
        )
    if item.nodo in contestados:
        return Veredicto(False, f"el ítem de «{item.nodo}» ya se contestó en esta sesión")

    razon = respuesta.razon.strip().lower()
    if ofrecido.razones and razon not in ofrecido.razones:
        return Veredicto(
            False, f"«{respuesta.razon}» no es una de las razones que se ofrecieron"
        )
    if item.opcion(respuesta.razon) is None:
        return Veredicto(False, f"«{respuesta.razon}» no es una razón de este ítem")
    if not respuesta.resultado.strip():
        return Veredicto(False, "la respuesta no trae resultado del turno 1")

    return Veredicto(True)

class Desenlace(str, Enum):

    SIN_RESPUESTA = "sin_respuesta"
    RECHAZADA = "rechazada"
    NO_CLASIFICABLE = "no_clasificable"
    PROCESADA = "procesada"

@dataclass(frozen=True)
class DesenlaceDelSondeo:

    estado: Desenlace = Desenlace.SIN_RESPUESTA

    nodo: str = ""

    motivo: str = ""

    @property
    def cierra_el_item(self) -> bool:
        return self.estado is Desenlace.PROCESADA

    @property
    def admitida(self) -> bool:
        return self.estado in (Desenlace.PROCESADA, Desenlace.NO_CLASIFICABLE)

@dataclass(frozen=True)
class EstadoDeSondeo:

    turnos_desde_el_ultimo: int = _TURNOS_ENTRE_SONDEOS

    ofrecidos: tuple[ItemOfrecido, ...] = field(default_factory=tuple)

    contestados: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nodos_ya_ofrecidos(self) -> tuple[str, ...]:
        return tuple(o.nodo for o in self.ofrecidos)

@dataclass(frozen=True)
class Ofrecimiento:

    item: ItemDosNiveles | None = None
    motivo: str = ""

    @property
    def procede(self) -> bool:
        return self.item is not None

def decidir(
    item: ItemDosNiveles | None,
    *,
    intencion: str = "",
    trae_expresion: bool = False,
    intentos_en_el_problema: int = 0,
    estado: EstadoDeSondeo | None = None,
    habilitado: bool = True,
    umbral_intentos: int = _INTENTOS_MINIMOS,
) -> Ofrecimiento:

    estado = estado or EstadoDeSondeo()

    if not habilitado:
        return Ofrecimiento(motivo="el sondeo de este nodo está congelado por decisión curricular")
    if item is None:
        return Ofrecimiento(motivo="no hay ítem escrito para el nodo de este turno")
    if not item.ofrecible:
        return Ofrecimiento(motivo=f"el ítem de {item.nodo} está incompleto para plantearlo")
    if item.nodo in estado.nodos_ya_ofrecidos:
        return Ofrecimiento(motivo=f"el ítem de {item.nodo} ya se planteó en esta sesión")
    if estado.turnos_desde_el_ultimo < _TURNOS_ENTRE_SONDEOS:
        return Ofrecimiento(
            motivo=f"solo han pasado {estado.turnos_desde_el_ultimo} turnos desde el último"
        )
    if not trae_expresion or intencion == "emocional":
        return Ofrecimiento(motivo="el turno no está resolviendo un ejercicio")
    if intentos_en_el_problema < umbral_intentos:
        return Ofrecimiento(motivo="la duda todavía no está sostenida")

    return Ofrecimiento(
        item=item,
        motivo=f"{intentos_en_el_problema} intentos en un ejercicio de {item.nodo}",
    )
