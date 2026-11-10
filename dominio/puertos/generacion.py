from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ErrorDeGeneracion(Exception):
    pass

@dataclass(frozen=True)
class PeticionDeGeneracion:

    instruccion: str
    temperatura: float = 0.0
    maximo_de_unidades: int = 800
    mensajes: tuple[dict, ...] = ()

    def validar(self) -> list[str]:
        fallos = []
        if any(m.get("role") not in ("system", "user", "assistant") or not isinstance(m.get("content"), str) for m in self.mensajes):
            fallos.append("mensajes de generación inválidos")
        if not self.instruccion.strip():
            fallos.append("instrucción vacía: no hay nada que generar")
        if not 0.0 <= self.temperatura <= 2.0:
            fallos.append(f"temperatura fuera de rango: {self.temperatura}")
        if self.maximo_de_unidades < 1:
            fallos.append(
                f"máximo de unidades inválido: {self.maximo_de_unidades}"
            )
        return fallos

@dataclass(frozen=True)
class RespuestaDeGeneracion:

    texto: str
    modelo: str = ""
    proveedor: str = ""
    unidades_de_entrada: int = 0
    unidades_de_salida: int = 0
    metadatos: dict = field(default_factory=dict)
    estructura: dict | None = None

    @property
    def sin_verificar(self) -> bool:
        return True

    @property
    def vacia(self) -> bool:
        return not self.texto.strip()

@runtime_checkable
class PuertoGeneracion(Protocol):

    def generar(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        ...
