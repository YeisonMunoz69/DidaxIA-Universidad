from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class PuertoAnaliticaDocente(Protocol):
    def directorio_de_estudiantes(
        self,
        actor: str,
        pagina: int,
        tamano: int,
        *,
        alcance_institucional: bool = False,
        buscar: str = "",
    ) -> dict:

        ...

    def resumen_de_clase(
        self, clase: str, docente: str, desde: datetime, hasta: datetime
    ) -> dict | None:

        ...

    def resumen_institucional(
        self, investigador: str, desde: datetime, hasta: datetime
    ) -> dict:

        ...

    def ficha_de_estudiante(
        self,
        clase: str,
        docente: str,
        estudiante: str,
        desde: datetime,
        hasta: datetime,
    ) -> dict | None:

        ...

    def actividad_de_clase(
        self,
        clase: str,
        actor: str,
        desde: datetime,
        hasta: datetime,
        *,
        metrica: str = "turnos",
        busqueda: str = "",
        solo_activos: bool = False,
        limite: int = 200,
        alcance_institucional: bool = False,
    ) -> dict | None:

        ...

    def detalle_institucional_de_clase(
        self, clase: str, investigador: str, desde: datetime, hasta: datetime
    ) -> dict | None:

        ...

    def ficha_institucional_de_estudiante(
        self, clase: str, investigador: str, estudiante: str,
        desde: datetime, hasta: datetime,
    ) -> dict | None:

        ...

    def corregir_perfil_de_estudiante(
        self, clase: str, actor: str, estudiante: str, datos_academicos: dict,
        *, alcance_institucional: bool = False,
    ) -> dict | None: ...

    def rectificar_edad(
        self, clase: str, actor: str, estudiante: str, edad_nueva: int, motivo: str
    ) -> dict | None:

        ...
