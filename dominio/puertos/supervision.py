from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_EDITADO = "editado"
ESTADO_RECHAZADO = "rechazado"


TIPO_RESPUESTA = "respuesta"
TIPO_SIN_FUENTE = "sin-fuente"
TIPO_DEGRADADO = "degradado"


@dataclass
class ItemDeRevision:

    identificador: str
    recibido: str
    urgencia: str
    clase: str | None
    tipo: str
    mensaje: str
    turno: dict
    estado: str = ESTADO_PENDIENTE

    concepcion_candidata: str | None = None
    ansiedad_estimada: float | None = None
    estudiante: str = ""
    sesion: str = ""

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "recibido": self.recibido,
            "urgencia": self.urgencia,
            "clase": self.clase,
            "tipo": self.tipo,
            "mensaje": self.mensaje,
            "turno": self.turno,
            "concepcion_candidata": self.concepcion_candidata,
            "ansiedad_estimada": self.ansiedad_estimada,
            "estudiante": self.estudiante,
            "sesion": self.sesion,
        }

@dataclass
class NuevoItem:

    urgencia: str
    clase: str | None
    tipo: str
    mensaje: str
    turno: dict
    concepcion_candidata: str | None = None
    ansiedad_estimada: float | None = None
    estudiante: str = ""
    sesion: str = ""

@dataclass(frozen=True)
class AclaracionDocente:

    identificador: str
    sesion: str
    texto: str
    docente: str
    creada_en: str

    turno: str = ""

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "sesion": self.sesion,
            "texto": self.texto,
            "docente": self.docente,
            "creada_en": self.creada_en,
            "turno": self.turno,
        }

@runtime_checkable
class PuertoColaDeRevision(Protocol):

    def agregar(self, nuevo: NuevoItem) -> ItemDeRevision:
        ...

    def listar_pendientes(
        self,
        urgencia: str = "",
        clase: str = "",
        tipo: str = "",
        tope: int | None = None,
        desde: int = 0,
        clases_permitidas: tuple[str, ...] = (),
    ) -> list[ItemDeRevision]:

        ...

    def total_pendientes(
        self, urgencia: str = "", clase: str = "", tipo: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> int:

        ...

    def aprobar(
        self, identificador: str, actor: str = "", clases_permitidas: tuple[str, ...] = ()
    ) -> bool:

        ...

    def editar(
        self, identificador: str, texto: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:

        ...

    def rechazar(
        self, identificador: str, motivo: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:

        ...

    def listar_aclaraciones(self, estudiante: str, sesion: str) -> list[AclaracionDocente]:
        ...
