from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class TelemetriaNoConfigurada:
    def registrar(self, *_args, **_kwargs) -> bool:
        raise AlmacenNoConfigurado("la telemetría de la Fase 8 necesita PostgreSQL")
