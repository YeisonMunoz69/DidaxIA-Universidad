"""Cálculo de indicadores cerrado cuando PostgreSQL no está configurado.

Falla cerrado y no devuelve un catálogo con ceros: un tablero lleno de ceros
por falta de base es exactamente el silencio que el encargo prohíbe. La ruta lo
traduce a mantenimiento, que sí dice lo que ocurre.
"""

from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class CalculoKPINoConfigurado:
    def calcular(self, *_args, **_kwargs) -> dict:
        raise AlmacenNoConfigurado("el catálogo KPI v1.1 necesita PostgreSQL")
