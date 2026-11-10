from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Reporte:
    identificador: int
    reportado_por: str
    rol: str
    categoria: str
    titulo: str
    descripcion: str
    pasos: str
    ruta: str
    estado: str
    tiene_captura: bool
    captura_bytes: int
    respuesta: str
    creado_en: datetime
    actualizado_en: datetime
    reportante: dict | None = None

class PuertoReportes(Protocol):
    def crear(
        self, *, actor: str, rol: str, categoria: str, titulo: str,
        descripcion: str, pasos: str, ruta: str, captura: bytes | None,
    ) -> Reporte: ...

    def mios(self, actor: str) -> tuple[Reporte, ...]: ...

    def captura_propia(self, actor: str, reporte: int) -> bytes | None: ...

    def institucionales(self, actor: str, estado: str = "") -> tuple[Reporte, ...]: ...

    def captura(self, actor: str, reporte: int) -> bytes | None: ...

    def actualizar(
        self, actor: str, reporte: int, *, estado: str, respuesta: str,
    ) -> Reporte: ...
