"""Contrato de la analítica descriptiva que alimenta el panel docente.

La unidad es un turno lógico —sujeto, sesión y turno—, no cada voz guardada.
El alcance actual es la cohorte matriculada hoy, desde la fecha de su matrícula;
no pretende reconstruir a qué clase perteneció un turno histórico anterior.
"""

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
        """Lista matrículas visibles, paginadas y ordenadas alfabéticamente.

        Con alcance docente sólo incluye clases creadas por ``actor``. El
        alcance institucional debe autorizar además al investigador y auditar
        la lectura antes de devolver cualquier identidad.
        """
        ...

    def resumen_de_clase(
        self, clase: str, docente: str, desde: datetime, hasta: datetime
    ) -> dict | None:
        """Devuelve KPI descriptivos o ``None`` si la clase no es del docente."""
        ...

    def resumen_institucional(
        self, investigador: str, desde: datetime, hasta: datetime
    ) -> dict:
        """Devuelve agregados institucionales tras autorizar y auditar la lectura."""
        ...

    def ficha_de_estudiante(
        self,
        clase: str,
        docente: str,
        estudiante: str,
        desde: datetime,
        hasta: datetime,
    ) -> dict | None:
        """Actividad e indicios de un integrante, o ``None`` fuera de alcance.

        La implementación debe comprobar en la misma lectura que ``clase``
        pertenece a ``docente`` y que ``estudiante`` está matriculado allí.
        """
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
        """Tabla comparativa de actividad, sin texto y sin consultas N+1."""
        ...

    def detalle_institucional_de_clase(
        self, clase: str, investigador: str, desde: datetime, hasta: datetime
    ) -> dict | None:
        """Curso, docente e integrantes para navegación institucional auditada."""
        ...

    def ficha_institucional_de_estudiante(
        self, clase: str, investigador: str, estudiante: str,
        desde: datetime, hasta: datetime,
    ) -> dict | None:
        """La misma base de seguimiento, accesible por el borde investigador."""
        ...

    def corregir_perfil_de_estudiante(
        self, clase: str, actor: str, estudiante: str, datos_academicos: dict,
        *, alcance_institucional: bool = False,
    ) -> dict | None: ...

    def rectificar_edad(
        self, clase: str, actor: str, estudiante: str, edad_nueva: int, motivo: str
    ) -> dict | None:
        """Rectificación institucional histórica, nunca disponible al titular."""
        ...
