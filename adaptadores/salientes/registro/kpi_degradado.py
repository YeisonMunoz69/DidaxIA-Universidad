from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class CalculoKPINoConfigurado:
    def calcular(self, *_args, **_kwargs) -> dict:
        raise AlmacenNoConfigurado("el catálogo KPI v1.1 necesita PostgreSQL")
