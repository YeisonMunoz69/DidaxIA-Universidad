from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace

from dominio.modelo.estudiante import Episodio, EstadoEstrategico
from dominio.pedagogia import estrategias as E
from dominio.pedagogia.intenciones import (
    BLOQUEO_EXPLICITO,
    PETICION_SOLUCION,
    Intencion,
)


_CORRIGEN = frozenset(
    {
        E.SCAFFOLDING_KQ,
        E.CONFLICTO_CONCEPTUAL,
        E.DESARROLLO_GUIADO,
    }
)

_ESPACIOS = re.compile(r"\s+")


_MAXIMO_ARCHIVADOS = 8


def normalizar_expresion(expresion: str) -> str:
    plano = unicodedata.normalize("NFD", expresion.strip().lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return _ESPACIOS.sub("", plano).rstrip(".,;:")

@dataclass(frozen=True)
class UnidadDeProblema:

    nodo: str = ""
    expresion: str = ""
    item: str = ""

    @property
    def identidad(self) -> str:
        if self.item:
            return f"item:{self.item}"
        if self.expresion:
            return f"expr:{normalizar_expresion(self.expresion)}"
        if self.nodo:
            return f"nodo:{self.nodo}"
        return ""

    @property
    def abierto(self) -> bool:
        return bool(self.identidad)

@dataclass(frozen=True)
class EstadoDelProblema:

    unidad: UnidadDeProblema = field(default_factory=UnidadDeProblema)
    intentos: int = 0
    insistencias: int = 0
    peticion_confirmada: bool = False

    expresiones_vistas: tuple[str, ...] = ()
    episodios: EstadoEstrategico = field(default_factory=EstadoEstrategico)

    estrategia_anterior: str = ""
    correccion_comprobada_anterior: bool = False

    archivados: tuple[tuple[str, EstadoDelProblema], ...] = ()

    @property
    def ciclo_negativo(self) -> bool:
        return self.episodios.ciclo_negativo

    @property
    def sesgo_de_confirmacion(self) -> bool:
        return self.episodios.sesgo_de_confirmacion

    def como_dict(self) -> dict:
        return {
            "unidad": {
                "nodo": self.unidad.nodo,
                "expresion": self.unidad.expresion,
                "item": self.unidad.item,
            },
            "intentos": self.intentos,
            "insistencias": self.insistencias,
            "peticion_confirmada": self.peticion_confirmada,
            "expresiones_vistas": list(self.expresiones_vistas),
            "episodios": [
                {
                    "retroalimentacion_correctiva": e.retroalimentacion_correctiva,
                    "reincide_en_la_estrategia": e.reincide_en_la_estrategia,
                    "confusion": e.confusion,
                    "afecto_negativo": e.afecto_negativo,
                    "evitacion_o_bajo_esfuerzo": e.evitacion_o_bajo_esfuerzo,
                }
                for e in self.episodios.episodios
            ],
            "estrategia_anterior": self.estrategia_anterior,
            "correccion_comprobada_anterior": self.correccion_comprobada_anterior,

            "archivados": [
                [identidad, estado.como_dict()] for identidad, estado in self.archivados
            ],
        }

    @classmethod
    def desde_dict(cls, crudo: dict) -> EstadoDelProblema:
        unidad = crudo.get("unidad") or {}
        return cls(
            unidad=UnidadDeProblema(
                nodo=str(unidad.get("nodo", "")),
                expresion=str(unidad.get("expresion", "")),
                item=str(unidad.get("item", "")),
            ),
            intentos=int(crudo.get("intentos", 0)),
            insistencias=int(crudo.get("insistencias", 0)),
            peticion_confirmada=bool(crudo.get("peticion_confirmada", False)),
            expresiones_vistas=tuple(crudo.get("expresiones_vistas", ())),
            episodios=EstadoEstrategico(
                episodios=tuple(Episodio(**e) for e in crudo.get("episodios", ()))
            ),
            estrategia_anterior=str(crudo.get("estrategia_anterior", "")),
            correccion_comprobada_anterior=bool(crudo.get("correccion_comprobada_anterior", False)),
            archivados=tuple(
                (str(identidad), cls.desde_dict(guardado))
                for identidad, guardado in crudo.get("archivados", ())
            ),
        )

@dataclass(frozen=True)
class Observacion:

    intencion: Intencion

    expresiones: tuple[str, ...] = ()

    expresiones_heredadas: bool = False

    nodo: str = ""

    item: str = ""

    veredicto: str = ""

    estrategia: str = ""

    base: str = ""
    propuesta: str = ""
    correccion_comprobada: bool = False

@dataclass(frozen=True)
class EventoDeConteo:

    problema_cambio: bool = False
    identidad: str = ""
    identidad_anterior: str = ""
    conto_intento: bool = False
    conto_insistencia: bool = False
    repeticion_ignorada: bool = False
    episodio_registrado: bool = False
    motivo: str = ""

    def como_dict(self) -> dict:
        return {
            "problema_cambio": self.problema_cambio,
            "identidad": self.identidad,
            "identidad_anterior": self.identidad_anterior,
            "conto_intento": self.conto_intento,
            "conto_insistencia": self.conto_insistencia,
            "repeticion_ignorada": self.repeticion_ignorada,
            "episodio_registrado": self.episodio_registrado,
            "motivo": self.motivo,
        }

def unidad_de(observacion: Observacion, actual: UnidadDeProblema) -> UnidadDeProblema:
    if observacion.item:
        return UnidadDeProblema(nodo=observacion.nodo or actual.nodo, item=observacion.item)
    if observacion.base:
        return UnidadDeProblema(nodo=observacion.nodo or actual.nodo, expresion=observacion.base)
    if observacion.expresiones_heredadas and observacion.expresiones:

        return actual if actual.abierto else UnidadDeProblema(
            nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
        )
    if observacion.expresiones:
        propone = observacion.intencion.propone_solucion
        if not propone or len(observacion.expresiones) >= 2:
            return UnidadDeProblema(
                nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
            )

        if actual.abierto:
            return actual
        return UnidadDeProblema(
            nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
        )
    if observacion.nodo and observacion.nodo != actual.nodo:
        return UnidadDeProblema(nodo=observacion.nodo)
    return actual

def _episodio(estado: EstadoDelProblema, observacion: Observacion, repetida: bool) -> Episodio:
    intencion = observacion.intencion
    return Episodio(

        retroalimentacion_correctiva=(
            (estado.estrategia_anterior in _CORRIGEN or estado.correccion_comprobada_anterior)
            and bool(estado.expresiones_vistas)
        ),
        reincide_en_la_estrategia=repetida,

        confusion=(
            intencion.clase == BLOQUEO_EXPLICITO or observacion.veredicto == "invalida"
        ),
        afecto_negativo=intencion.carga_emocional_expresada,

        evitacion_o_bajo_esfuerzo=intencion.clase == PETICION_SOLUCION,
    )

def _contar(
    estado: EstadoDelProblema, intencion: Intencion, repetida: bool
) -> tuple[EstadoDelProblema, bool, bool, bool, str]:

    if intencion.confirma_ayuda:
        return (
            replace(estado, peticion_confirmada=True),
            False,
            False,
            False,
            "confirmó la ayuda que se le ofreció (RF-GEN-05)",
        )
    if intencion.clase == PETICION_SOLUCION:
        return (
            replace(estado, insistencias=estado.insistencias + 1),
            False,
            True,
            False,
            "pidió la respuesta: insistir no escala (RF-GEN-04)",
        )
    if intencion.propone_solucion and repetida:

        return (
            estado,
            False,
            False,
            True,
            "repite una expresión ya escrita en este problema: no es un intento nuevo",
        )
    if intencion.propone_solucion:
        return (
            replace(estado, intentos=estado.intentos + 1),
            True,
            False,
            False,
            "propuso algo nuevo sobre este problema",
        )
    return estado, False, False, False, "el turno no aporta ni pide: no mueve ningún contador"

def _cambiar_de_problema(
    estado: EstadoDelProblema, unidad: UnidadDeProblema
) -> EstadoDelProblema:

    saliente = estado.unidad.identidad

    guardado = replace(estado, archivados=())
    archivo = [(clave, valor) for clave, valor in estado.archivados if clave != saliente]
    if saliente:
        archivo.append((saliente, guardado))
    archivo = archivo[-_MAXIMO_ARCHIVADOS:]

    entrante = unidad.identidad
    recuperado = next((valor for clave, valor in archivo if clave == entrante), None)
    if recuperado is not None:
        archivo = [(clave, valor) for clave, valor in archivo if clave != entrante]
        return replace(recuperado, unidad=unidad, archivados=tuple(archivo))
    return EstadoDelProblema(unidad=unidad, archivados=tuple(archivo))

def observar(
    estado: EstadoDelProblema, observacion: Observacion
) -> tuple[EstadoDelProblema, EventoDeConteo]:

    unidad = unidad_de(observacion, estado.unidad)
    anterior = estado.unidad.identidad
    cambio = bool(anterior) and unidad.identidad != anterior

    estado = (
        _cambiar_de_problema(estado, unidad) if cambio else replace(estado, unidad=unidad)
    )

    intencion = observacion.intencion
    estado = replace(estado, peticion_confirmada=False)
    escritas = (observacion.propuesta,) if observacion.propuesta else (
        () if observacion.expresiones_heredadas else observacion.expresiones
    )
    nuevas = tuple(normalizar_expresion(e) for e in escritas if e.strip())
    repetida = bool(nuevas) and all(e in estado.expresiones_vistas for e in nuevas)

    estado, conto_intento, conto_insistencia, repeticion_ignorada, motivo = _contar(
        estado, intencion, repetida
    )

    if nuevas:
        vistas = list(estado.expresiones_vistas)
        for e in nuevas:
            if e not in vistas:
                vistas.append(e)
        estado = replace(estado, expresiones_vistas=tuple(vistas))

    episodio_registrado = False
    if estado.unidad.abierto and (
        conto_intento or conto_insistencia or repeticion_ignorada
    ):
        episodios, _ = estado.episodios.registrar(
            _episodio(estado, observacion, repetida), turno=""
        )
        estado = replace(estado, episodios=episodios)
        episodio_registrado = True

    if observacion.estrategia:
        estado = replace(estado, estrategia_anterior=observacion.estrategia)
    estado = replace(estado, correccion_comprobada_anterior=observacion.correccion_comprobada)

    return estado, EventoDeConteo(
        problema_cambio=cambio,
        identidad=unidad.identidad,
        identidad_anterior=anterior,
        conto_intento=conto_intento,
        conto_insistencia=conto_insistencia,
        repeticion_ignorada=repeticion_ignorada,
        episodio_registrado=episodio_registrado,
        motivo=motivo,
    )

def reiniciar_por_cambio_de_problema(
    estado: EstadoDelProblema, intencion: Intencion, expresiones: tuple[str, ...], *, base: str = ""
) -> tuple[EstadoDelProblema, bool]:

    unidad = unidad_de(
        Observacion(intencion=intencion, expresiones=expresiones, base=base), estado.unidad
    )
    anterior = estado.unidad.identidad
    if anterior and unidad.identidad != anterior:
        return EstadoDelProblema(unidad=unidad), True
    return estado, False
