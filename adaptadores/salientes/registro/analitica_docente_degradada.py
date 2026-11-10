"""Analítica cerrada cuando PostgreSQL no está configurado."""

from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class AnaliticaDocenteNoConfigurada:
    def directorio_de_estudiantes(self, *_args, **_kwargs) -> dict:
        raise AlmacenNoConfigurado("el directorio de estudiantes necesita PostgreSQL")

    def resumen_de_clase(self, *_args, **_kwargs) -> dict | None:
        raise AlmacenNoConfigurado("la analítica docente necesita PostgreSQL")

    def resumen_institucional(self, *_args, **_kwargs) -> dict:
        raise AlmacenNoConfigurado("la analítica institucional necesita PostgreSQL")

    def ficha_de_estudiante(self, *_args, **_kwargs) -> dict | None:
        raise AlmacenNoConfigurado("la ficha analítica necesita PostgreSQL")

    def detalle_institucional_de_clase(self, *_args, **_kwargs) -> dict | None:
        raise AlmacenNoConfigurado("el detalle institucional necesita PostgreSQL")

    def ficha_institucional_de_estudiante(self, *_args, **_kwargs) -> dict | None:
        raise AlmacenNoConfigurado("la ficha institucional necesita PostgreSQL")
