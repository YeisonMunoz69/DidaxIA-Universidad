from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

SOLICITUDES_MATRICULA = "solicitudes_matricula"


@dataclass(frozen=True)
class CategoriaDeNotificacion:
    codigo: str
    titulo: str
    descripcion: str
    predeterminado: bool = False

    def como_json(self) -> dict:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "predeterminado": self.predeterminado,
        }

CATEGORIAS = {
    SOLICITUDES_MATRICULA: CategoriaDeNotificacion(
        codigo=SOLICITUDES_MATRICULA,
        titulo="Solicitudes de ingreso a clases",
        descripcion=(
            "Envía un correo por cada solicitud nueva. Aunque esté desactivado, "
            "la solicitud siempre queda disponible dentro de DidaxIa."
        ),
    ),
}


def valores_predeterminados() -> dict[str, bool]:
    return {codigo: categoria.predeterminado for codigo, categoria in CATEGORIAS.items()}

@runtime_checkable
class PuertoPreferenciasDeNotificacion(Protocol):
    def consultar(self, sujeto: str) -> dict[str, bool]:
        ...

    def guardar(self, sujeto: str, categoria: str, habilitada: bool) -> dict[str, bool]:
        ...

    def habilitada(self, sujeto: str, categoria: str) -> bool:
        ...

    def habilitada_para_correo(self, correo: str, categoria: str) -> bool:
        ...
