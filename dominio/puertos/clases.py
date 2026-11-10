from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ConflictoDeMatricula(ValueError):
    pass

@dataclass(frozen=True)
class ContextoCurricular:

    clase: str
    unidad: str = ""
    notacion: str = "sen"
    observaciones: str = ""
    actualizado_en: str | None = None

    def como_json(self) -> dict:
        return {
            "clase": self.clase,
            "unidad": self.unidad,
            "notacion": self.notacion,
            "observaciones": self.observaciones,
            "actualizado_en": self.actualizado_en,
        }

@dataclass(frozen=True)
class SolicitudDeMatricula:
    identificador: str
    estudiante: str
    clase_destino: str
    nombre_destino: str
    clase_origen: str | None
    nombre_origen: str | None
    clase_actual: str | None
    nombre_actual: str | None
    estado: str
    creada_en: str
    resuelta_en: str | None = None
    resuelta_por: str | None = None
    nombre_estudiante: str = ""
    correo_docente: str = ""
    nombre_docente: str = ""
    facultad_estudiante: str = ""
    programa_estudiante: str = ""
    semestre_estudiante: int | None = None
    docente: str = ""

    def como_elemento(self) -> dict:
        def referencia(identificador, nombre):
            return {"id": identificador, "nombre": nombre} if identificador else None

        elemento = {
            "id": self.identificador,
            "estudiante": self.estudiante,
            "nombre_estudiante": self.nombre_estudiante.strip(),
            "clase_destino": referencia(self.clase_destino, self.nombre_destino),
            "clase_origen": referencia(self.clase_origen, self.nombre_origen),
            "clase_actual": referencia(self.clase_actual, self.nombre_actual),
            "estado": self.estado,
            "creada_en": self.creada_en,
            "resuelta_en": self.resuelta_en,
            "resuelta_por": self.resuelta_por,
        }
        if self.facultad_estudiante or self.programa_estudiante or self.semestre_estudiante:
            elemento["perfil_estudiante"] = {
                "facultad": self.facultad_estudiante.strip(),
                "programa": self.programa_estudiante.strip(),
                "semestre": self.semestre_estudiante,
            }
        return elemento

@dataclass
class Matricula:

    identificador: str
    desde: str
    nombre: str = ""
    foto_referencia: str = ""
    facultad: str = ""
    programa: str = ""
    semestre: int | None = None

    def como_fila(self) -> dict:
        return {
            "identificador": self.identificador,
            "nombre": self.nombre.strip() or f"Estudiante {self.identificador[:8]}",
            "desde": self.desde,
            "tiene_foto": bool(self.foto_referencia),
            "facultad": self.facultad.strip(),
            "programa": self.programa.strip(),
            "semestre": self.semestre,
        }

@dataclass
class Clase:
    identificador: str
    nombre: str
    creador: str
    codigo: str
    matriculados: dict[str, Matricula] = field(default_factory=dict)

    def como_resumen(self) -> dict:
        return {
            "id": self.identificador,
            "nombre": self.nombre,
            "codigo": self.codigo,
            "integrantes": len(self.matriculados),
        }

@runtime_checkable
class PuertoClases(Protocol):

    def crear(self, nombre: str, creador: str) -> Clase:
        ...

    def unirse(self, codigo: str, identificador: str) -> SolicitudDeMatricula | None:
        ...

    def solicitudes(self, quien: str, rol: str) -> list[SolicitudDeMatricula]:
        ...

    def resolver_solicitud(
        self, identificador: str, quien: str, rol: str, decision: str
    ) -> SolicitudDeMatricula | None:

        ...

    def regenerar_codigo(self, identificador: str, quien: str) -> str | None:
        ...

    def renombrar(self, identificador: str, quien: str, nombre: str) -> Clase | None:
        ...

    def archivar(self, identificador: str, quien: str, motivo: str, rol: str = "docente") -> bool:
        ...

    def mias(self, identificador: str) -> list[Clase]:
        ...

    def integrantes(self, identificador: str, quien: str) -> list[Matricula] | None:
        ...

    def retirar_integrante(
        self, identificador: str, quien: str, estudiante: str, motivo: str
    ) -> Matricula | None:

        ...

    def contexto_curricular(self, identificador: str, quien: str) -> ContextoCurricular | None:
        ...

    def guardar_contexto_curricular(
        self, identificador: str, quien: str, unidad: str, notacion: str, observaciones: str
    ) -> ContextoCurricular | None:

        ...

    def integrante_para_investigacion(
        self, identificador: str, investigador: str, estudiante: str
    ) -> Matricula | None:

        ...

    def suprimir_sujeto(self, identificador: str) -> int:
        ...
