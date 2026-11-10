from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class RegistroConsumoIA:

    llamada: UUID
    instante_utc: datetime
    proveedor: str
    modelo_solicitado: str
    modelo_respondido: str = ""
    respuesta_proveedor: str = ""
    local: bool = False
    estado: str = "sin_medicion"
    reintento: int = 0
    entrada_cache_hit: int | None = None
    entrada_cache_miss: int | None = None
    entrada_total: int | None = None
    salida: int | None = None
    total: int | None = None

    def __post_init__(self) -> None:
        if self.instante_utc.tzinfo is None:
            raise ValueError("el instante de consumo debe incluir zona horaria")
        if self.estado not in {"completada", "fallida", "sin_medicion"}:
            raise ValueError("estado de consumo no admitido")
        if not self.proveedor.strip() or not self.modelo_solicitado.strip():
            raise ValueError("proveedor y modelo solicitado son obligatorios")
        if self.reintento < 0:
            raise ValueError("el número de reintento no puede ser negativo")
        valores = (
            self.entrada_cache_hit,
            self.entrada_cache_miss,
            self.entrada_total,
            self.salida,
            self.total,
        )
        if any(valor is not None and valor < 0 for valor in valores):
            raise ValueError("los tokens no pueden ser negativos")

    @property
    def medido(self) -> bool:
        return self.entrada_total is not None and self.salida is not None

@runtime_checkable
class RegistradorConsumoIA(Protocol):
    def registrar(self, registro: RegistroConsumoIA) -> bool:
        ...

@dataclass(frozen=True)
class TarifaIA:
    proveedor: str
    modelo: str
    franja: str
    vigente_desde: datetime
    vigente_hasta: datetime | None
    entrada_cache_hit_usd_millon: Decimal
    entrada_cache_miss_usd_millon: Decimal
    salida_usd_millon: Decimal
    fuente: str

    def aplica(self, registro: RegistroConsumoIA) -> bool:
        instante = registro.instante_utc.astimezone(UTC)
        return (
            registro.proveedor == self.proveedor
            and registro.modelo_respondido == self.modelo
            and self.franja == franja_tarifaria_deepseek(instante)
            and self.vigente_desde <= instante
            and (self.vigente_hasta is None or instante < self.vigente_hasta)
        )

def franja_tarifaria_deepseek(instante: datetime) -> str:
    utc = instante.astimezone(UTC)
    if utc.weekday() >= 5:
        return "fuera_pico"
    hora = utc.time().replace(tzinfo=None)
    if time(1) <= hora < time(4) or time(6) <= hora < time(10):
        return "pico"
    return "fuera_pico"

def costo_estimado_usd(
    registro: RegistroConsumoIA, tarifa: TarifaIA | None
) -> Decimal | None:

    if registro.local:
        return Decimal("0")
    if tarifa is None:
        return None
    necesarios = (registro.entrada_cache_hit, registro.entrada_cache_miss, registro.salida)
    if any(valor is None for valor in necesarios):
        return None
    costo = (
        Decimal(registro.entrada_cache_hit or 0)
        * tarifa.entrada_cache_hit_usd_millon
        + Decimal(registro.entrada_cache_miss or 0)
        * tarifa.entrada_cache_miss_usd_millon
        + Decimal(registro.salida or 0) * tarifa.salida_usd_millon
    ) / Decimal("1000000")
    return costo.quantize(Decimal("0.000000000001"))
