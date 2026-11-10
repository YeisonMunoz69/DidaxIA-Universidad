"""Evolución versionada del esquema PostgreSQL de DidaxIA."""

from infraestructura.migraciones.ejecutor import (
    BaseExistenteSinLineaBase,
    EsquemaParcial,
    HistorialIncompatible,
    MigracionEnCurso,
    MigracionRequiereDecision,
    Resultado,
    ejecutar,
)

__all__ = [
    "BaseExistenteSinLineaBase",
    "EsquemaParcial",
    "HistorialIncompatible",
    "MigracionEnCurso",
    "MigracionRequiereDecision",
    "Resultado",
    "ejecutar",
]
