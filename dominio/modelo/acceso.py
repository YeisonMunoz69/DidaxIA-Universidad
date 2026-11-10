from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.consentimiento import EstadoConsentimiento
from dominio.modelo.identidad import CategoriaDeEdad, PerfilOnboarding
from dominio.modelo.menores import EstadoAsentimiento, EstadoRepresentante


class AccesoCalculado(StrEnum):

    ONBOARDING_PENDIENTE = "onboarding_pendiente"
    ESPERANDO_REPRESENTANTE = "esperando_representante"
    HABILITADO = "habilitado"
    BLOQUEADO_POR_RECHAZO = "bloqueado_por_rechazo"
    BLOQUEADO_POR_REVOCACION = "bloqueado_por_revocacion"
    ELIMINACION_SOLICITADA = "eliminacion_solicitada"
    MANTENIMIENTO = "mantenimiento"

ACCESOS_CON_TUTOR: frozenset[AccesoCalculado] = frozenset({AccesoCalculado.HABILITADO})


@dataclass(frozen=True, slots=True)
class VersionesRequeridas:

    titular: str | None = None
    asentimiento: str | None = None
    representante: str | None = None

@dataclass(frozen=True, slots=True)
class EstadoVigente:

    sujeto_google: str
    perfil: PerfilOnboarding | None = None
    consentimiento: EstadoConsentimiento = EstadoConsentimiento.PENDIENTE
    version_consentimiento: str | None = None

    evento_consentimiento: int | None = None

    categoria_edad_consentimiento: CategoriaDeEdad | None = None
    representante: EstadoRepresentante = EstadoRepresentante.NO_REQUERIDO

    motivo_representante: str = ""
    asentimiento: EstadoAsentimiento = EstadoAsentimiento.NO_REQUERIDO
    version_asentimiento: str | None = None

    requeridas: VersionesRequeridas = field(default_factory=VersionesRequeridas)
    limite_representante: datetime | None = None

    eliminacion_solicitada: bool = False

    tutoria_academica_sin_investigacion: bool = False

    @property
    def es_menor(self) -> bool:
        return self.perfil is not None and self.perfil.es_menor

    @property
    def perfil_completo(self) -> bool:
        return self.perfil is not None and self.perfil.completo

    @property
    def consentimiento_al_dia(self) -> bool:
        return (
            self.consentimiento is EstadoConsentimiento.OTORGADO
            and self.requeridas.titular is not None
            and self.version_consentimiento == self.requeridas.titular
            and self.perfil is not None
            and self.categoria_edad_consentimiento is not None
            and self.categoria_edad_consentimiento is self.perfil.categoria_de_edad
        )

    @property
    def asentimiento_al_dia(self) -> bool:
        return (
            self.asentimiento is EstadoAsentimiento.OTORGADO
            and self.requeridas.asentimiento is not None
            and self.version_asentimiento == self.requeridas.asentimiento
        )

def _hay_revocacion(estado: EstadoVigente) -> bool:
    if estado.consentimiento is EstadoConsentimiento.REVOCADO:
        return True
    return estado.es_menor and estado.asentimiento is EstadoAsentimiento.REVOCADO

def _hay_rechazo(estado: EstadoVigente) -> bool:
    if estado.consentimiento is EstadoConsentimiento.RECHAZADO:
        return True
    if not estado.es_menor:
        return False
    return (
        estado.asentimiento is EstadoAsentimiento.RECHAZADO
        or estado.representante is EstadoRepresentante.RECHAZADO
    )

def _menor_habilitado(estado: EstadoVigente) -> bool:
    return estado.representante is EstadoRepresentante.APROBADO and estado.asentimiento_al_dia

def calcular_acceso(
    estado: EstadoVigente, *, almacen_disponible: bool = True
) -> AccesoCalculado:

    if not almacen_disponible:
        return AccesoCalculado.MANTENIMIENTO
    if estado.eliminacion_solicitada:
        return AccesoCalculado.ELIMINACION_SOLICITADA
    if _hay_revocacion(estado):
        return AccesoCalculado.BLOQUEADO_POR_REVOCACION
    if _hay_rechazo(estado):
        return AccesoCalculado.BLOQUEADO_POR_RECHAZO
    if not estado.perfil_completo:
        return AccesoCalculado.ONBOARDING_PENDIENTE

    if not estado.consentimiento_al_dia:
        return AccesoCalculado.ONBOARDING_PENDIENTE
    if estado.es_menor and not _menor_habilitado(estado):
        return AccesoCalculado.ESPERANDO_REPRESENTANTE
    return AccesoCalculado.HABILITADO

def permite_tutor(acceso: AccesoCalculado) -> bool:
    return acceso in ACCESOS_CON_TUTOR

def permite_tutoria_academica(estado: EstadoVigente) -> bool:
    return (
        estado.tutoria_academica_sin_investigacion
        and estado.perfil_completo
        and not estado.eliminacion_solicitada
        and (not estado.es_menor or _menor_habilitado(estado))
    )

def permite_escritura_longitudinal(acceso: AccesoCalculado) -> bool:
    return acceso is AccesoCalculado.HABILITADO
