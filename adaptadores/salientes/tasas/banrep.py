"""Cliente mínimo del servicio SDMX oficial del Banco de la República."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlencode
from xml.etree import ElementTree

BASE = "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data"
FLUJO_HISTORICO = "ESTAT,DF_TRM_DAILY_HIST,1.0"
FLUJO_ULTIMA = "ESTAT,DF_TRM_DAILY_LATEST,1.0"
FUENTE = "Banco de la República · servicio SDMX de TRM"


class Transporte(Protocol):
    def obtener(self, url: str) -> bytes: ...


class TransporteUrllib:
    def obtener(self, url: str) -> bytes:
        import urllib.request

        peticion = urllib.request.Request(url, headers={"Accept": "application/xml"})
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            return respuesta.read()


@dataclass(frozen=True)
class ObservacionTRM:
    fecha: date
    pesos_por_usd: Decimal


class ClienteTRMBanrep:
    def __init__(self, transporte: Transporte | None = None) -> None:
        self._transporte = transporte or TransporteUrllib()

    def historica(self, desde: date, hasta: date) -> tuple[ObservacionTRM, ...]:
        if hasta < desde:
            raise ValueError("el intervalo de TRM está invertido")
        return self._consultar(FLUJO_HISTORICO, desde, hasta)

    def ultima(self) -> ObservacionTRM | None:
        observaciones = self._consultar(FLUJO_ULTIMA, None, None)
        return max(observaciones, key=lambda observacion: observacion.fecha, default=None)

    def _consultar(
        self, flujo: str, desde: date | None, hasta: date | None
    ) -> tuple[ObservacionTRM, ...]:
        parametros = {"dimensionAtObservation": "TIME_PERIOD", "detail": "full"}
        if desde is not None:
            parametros["startPeriod"] = desde.isoformat()
        if hasta is not None:
            parametros["endPeriod"] = hasta.isoformat()
        url = f"{BASE}/{flujo}/all?{urlencode(parametros)}"
        return _extraer(self._transporte.obtener(url))


def _extraer(documento: bytes) -> tuple[ObservacionTRM, ...]:
    """Acepta SDMX genérico y compacto sin acoplarse a prefijos XML."""
    raiz = ElementTree.fromstring(documento)
    salida: dict[date, Decimal] = {}
    for elemento in raiz.iter():
        if elemento.tag.rsplit("}", 1)[-1] != "Obs":
            continue
        periodo = elemento.attrib.get("TIME_PERIOD")
        valor = elemento.attrib.get("OBS_VALUE")
        for hijo in elemento:
            nombre = hijo.tag.rsplit("}", 1)[-1]
            if nombre == "ObsDimension":
                periodo = hijo.attrib.get("value", periodo)
            elif nombre == "ObsValue":
                valor = hijo.attrib.get("value", valor)
        try:
            if periodo and valor:
                salida[date.fromisoformat(periodo[:10])] = Decimal(valor)
        except (ValueError, InvalidOperation):
            continue
    return tuple(ObservacionTRM(fecha, salida[fecha]) for fecha in sorted(salida))
