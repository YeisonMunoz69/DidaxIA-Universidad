from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from dominio.modelo.calendario import es_habil, sumar_dias_habiles


HORAS_PARA_CANCELAR = 24


DIAS_HABILES_PARA_RESOLVER = 15
DIAS_HABILES_DE_EXTENSION = 8


SEGUNDOS_DE_REAUTENTICACION_RECIENTE = 5 * 60


TOLERANCIA_DE_RELOJ_SEGUNDOS = 30


FRASE_DE_CONFIRMACION = "ELIMINAR MIS DATOS"


class SupresionInvalida(ValueError):
    pass

class EstadoSupresion(StrEnum):

    SOLICITADA = "solicitada"
    CANCELADA = "cancelada"
    EJECUTADA = "ejecutada"
    RECHAZADA = "rechazada"

__all__ = [
    "DIAS_HABILES_DE_EXTENSION",
    "DIAS_HABILES_PARA_RESOLVER",
    "FRASE_DE_CONFIRMACION",
    "HORAS_PARA_CANCELAR",
    "SEGUNDOS_DE_REAUTENTICACION_RECIENTE",
    "TOLERANCIA_DE_RELOJ_SEGUNDOS",
    "EstadoSupresion",
    "SolicitudDeSupresion",
    "SupresionInvalida",
    "emision_recien_firmada",
    "es_habil",
    "extension_de",
    "frase_correcta",
    "plazos_de",
    "reautenticacion_reciente",
    "sumar_dias_habiles",
]


def reautenticacion_reciente(reautenticada_en: datetime, ahora: datetime) -> bool:
    if reautenticada_en > ahora:
        return False
    return (ahora - reautenticada_en).total_seconds() <= SEGUNDOS_DE_REAUTENTICACION_RECIENTE

def emision_recien_firmada(
    emitido_en: datetime | None,
    ahora: datetime,
    *,
    autenticado_en: datetime | None = None,
) -> bool:

    if emitido_en is None:
        return False
    if not _dentro_de_la_ventana(emitido_en, ahora):
        return False
    if autenticado_en is None:
        return True
    if not _dentro_de_la_ventana(autenticado_en, ahora):
        return False

    return (autenticado_en - emitido_en).total_seconds() <= TOLERANCIA_DE_RELOJ_SEGUNDOS

def _dentro_de_la_ventana(momento: datetime, ahora: datetime) -> bool:
    desfase = (ahora - momento).total_seconds()
    if desfase < -TOLERANCIA_DE_RELOJ_SEGUNDOS:
        return False
    return desfase <= SEGUNDOS_DE_REAUTENTICACION_RECIENTE + TOLERANCIA_DE_RELOJ_SEGUNDOS

def frase_correcta(escrita: str) -> bool:
    return (escrita or "").strip().casefold() == FRASE_DE_CONFIRMACION.casefold()

@dataclass(frozen=True, slots=True)
class SolicitudDeSupresion:

    sujeto_google: str
    estado: EstadoSupresion
    solicitada_en: datetime
    cancelable_hasta: datetime
    resolver_antes_de: datetime
    solicitada_por: str = ""
    extension_hasta: datetime | None = None
    extension_motivo: str = ""
    cerrada_en: datetime | None = None
    secuencia: int = 0

    @property
    def abierta(self) -> bool:
        return self.estado is EstadoSupresion.SOLICITADA

    def cancelable_en(self, ahora: datetime) -> bool:
        return self.abierta and ahora <= self.cancelable_hasta

    @property
    def plazo_vigente(self) -> datetime:
        return self.extension_hasta or self.resolver_antes_de

def plazos_de(solicitada_en: datetime) -> tuple[datetime, datetime]:
    return (
        solicitada_en + timedelta(hours=HORAS_PARA_CANCELAR),
        sumar_dias_habiles(solicitada_en, DIAS_HABILES_PARA_RESOLVER),
    )

def extension_de(resolver_antes_de: datetime) -> datetime:
    return sumar_dias_habiles(resolver_antes_de, DIAS_HABILES_DE_EXTENSION)
