"""
kpi.py — El contrato de lectura del catálogo KPI v1.1
======================================================

Un método. Recibe una `ConsultaKPI` ya validada y devuelve el cuerpo completo:
periodo, filtros aplicados, población y la lista de indicadores del alcance,
cada uno con su estado.

Por qué devuelve **todos** los del alcance y no sólo los calculables
-----------------------------------------------------------------------------
Porque un indicador ausente de la respuesta es indistinguible de uno que dio
cero. El encargo lo prohíbe con nombre propio, así que la lista incluye los no
instrumentados con su estado y con lo que exactamente les falta: quien lee el
tablero ve el hueco, no un espacio en blanco.


"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from dominio.kpi.consulta import ConsultaKPI


@runtime_checkable
class PuertoCalculoKPI(Protocol):
    def calcular(self, consulta: ConsultaKPI) -> dict:
        """Calcula los indicadores del alcance.

        La implementación tiene que autorizar y auditar **dentro de la misma
        transacción** en la que lee. Un docente sólo puede alcanzar sus clases;
        un investigador, la institución, y su lectura queda registrada.
        """
        ...
