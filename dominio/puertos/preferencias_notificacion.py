"""Preferencias individuales para avisos opcionales por correo.

La bandeja interna no depende de este puerto. Una preferencia decide solamente
si un hecho que ya quedó persistido produce además un correo. Los avisos
esenciales de seguridad, privacidad, recuperación y gobierno no forman parte
de este catálogo y, por tanto, no se pueden apagar accidentalmente desde aquí.
"""

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
        """Preferencias del sujeto, completadas con los valores por defecto."""
        ...

    def guardar(self, sujeto: str, categoria: str, habilitada: bool) -> dict[str, bool]:
        """Persiste una categoría y devuelve el conjunto completo vigente."""
        ...

    def habilitada(self, sujeto: str, categoria: str) -> bool:
        """Decide el envío a un sujeto estable; una fila ausente es ``False``."""
        ...

    def habilitada_para_correo(self, correo: str, categoria: str) -> bool:
        """Decide el envío a un buzón configurado que corresponde a una persona."""
        ...
