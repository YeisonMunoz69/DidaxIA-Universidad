from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class PreferenciasDeNotificacionNoConfiguradas:
    def consultar(self, *_args, **_kwargs) -> dict[str, bool]:
        raise AlmacenNoConfigurado("las preferencias de notificación necesitan PostgreSQL")

    def guardar(self, *_args, **_kwargs) -> dict[str, bool]:
        raise AlmacenNoConfigurado("las preferencias de notificación necesitan PostgreSQL")

    def habilitada(self, *_args, **_kwargs) -> bool:
        return False

    def habilitada_para_correo(self, *_args, **_kwargs) -> bool:
        return False
