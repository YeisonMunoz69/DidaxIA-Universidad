from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.propuestas import Propuesta
from dominio.modelo.supresion import SolicitudDeSupresion
from dominio.puertos.almacen import EscrituraRechazada


class SupresionEnCurso(EscrituraRechazada):
    pass

@runtime_checkable
class PuertoSolicitudesDeSupresion(Protocol):

    def abrir(
        self,
        sujeto_google: str,
        *,
        reautenticada_en: datetime,
        frase: str,
        actor: str = "",
    ) -> SolicitudDeSupresion:

        ...

    def cancelar(self, sujeto_google: str, *, ahora: datetime, actor: str = "") -> bool:
        ...

    def abierta_de(self, sujeto_google: str) -> SolicitudDeSupresion | None:
        ...

    def historial(self, sujeto_google: str) -> tuple[SolicitudDeSupresion, ...]:
        ...

@dataclass(frozen=True, slots=True)
class Retencion:

    sustentacion_en: datetime | None = None
    meses_despues: int = 6
    nota: str = ""

    @property
    def limite(self) -> datetime | None:
        if self.sustentacion_en is None:
            return None
        from dominio.modelo.calendario import sumar_meses

        return sumar_meses(self.sustentacion_en, self.meses_despues)

@runtime_checkable
class PuertoRetencion(Protocol):

    def vigente(self) -> Retencion:
        ...

    def fijar(
        self, sustentacion_en: datetime, *, registrada_por: str, meses_despues: int = 6
    ) -> Retencion:

        ...

@dataclass(frozen=True, slots=True)
class OperacionAuditada:

    operacion: str
    actor: str
    momento: datetime
    sujeto_afectado: str | None = None
    detalle: dict | None = None
    exige_doble_aprobacion: bool = False
    aprobada_por: str | None = None
    secuencia: int = 0

@runtime_checkable
class PuertoAuditoria(Protocol):

    def registrar(
        self,
        operacion: str,
        *,
        actor: str,
        sujeto_afectado: str | None = None,
        detalle: dict | None = None,
        exige_doble_aprobacion: bool = False,
        aprobada_por: str | None = None,
    ) -> OperacionAuditada:

        ...

    def de(self, sujeto_google: str) -> tuple[OperacionAuditada, ...]:
        ...

    def consultar_institucional(
        self, actor: str, pagina: int, tamano: int, *,
        operacion: str = "", actor_filtro: str = "", sujeto_filtro: str = "",
        desde: datetime | None = None, hasta: datetime | None = None,
        categoria: str = "", doble_aprobacion: str = "",
    ) -> dict:

        ...

    def informe_institucional(
        self, actor: str, *, filtros: dict, confirmado: bool,
        corte_instante: datetime,
    ) -> tuple[bytes, dict]:

        ...

@runtime_checkable
class PuertoNotificacion(Protocol):

    def avisar(
        self,
        correo: str,
        asunto: str,
        cuerpo: str,
        *,
        clave_idempotencia: str,
        html: str = "",
        adjuntos: tuple[dict[str, str], ...] = (),
    ) -> bool:

        ...

@runtime_checkable
class PuertoPropuestas(Protocol):

    def crear(self, operacion: str, payload: dict, *, propuesta_por: str) -> Propuesta:
        ...

    def aprobar(self, identificador: int, *, aprobador: str) -> Propuesta:
        ...

    def consultar(self, identificador: int) -> Propuesta | None:
        ...

    def pendientes(self) -> tuple[Propuesta, ...]:
        ...
