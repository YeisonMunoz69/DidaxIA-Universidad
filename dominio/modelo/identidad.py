from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


MAYORIA_DE_EDAD = 18


EDAD_MINIMA_ADMISIBLE = 0
EDAD_MAXIMA_ADMISIBLE = 120


SEMESTRE_MINIMO_ADMISIBLE = 1
SEMESTRE_MAXIMO_ADMISIBLE = 20


class IdentidadInvalida(ValueError):
    pass

class CategoriaDeEdad(StrEnum):

    MENOR = "menor"
    ADULTO = "adulto"
    NO_DECLARADA = "no_declarada"

def categoria_de_edad(edad: int | None) -> CategoriaDeEdad:
    if edad is None:
        return CategoriaDeEdad.NO_DECLARADA
    return CategoriaDeEdad.MENOR if edad < MAYORIA_DE_EDAD else CategoriaDeEdad.ADULTO

def _texto_obligatorio(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise IdentidadInvalida(f"{campo} no puede quedar vacío")
    return valor.strip()

def _entero_o_nada(valor: int | None, campo: str, minimo: int, maximo: int) -> int | None:
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise IdentidadInvalida(f"{campo} tiene que ser un entero o quedar sin declarar")
    if not minimo <= valor <= maximo:
        raise IdentidadInvalida(f"{campo} fuera del rango admisible [{minimo}, {maximo}]")
    return valor

def exigir_edad_admisible(edad: int | None) -> int | None:
    return _entero_o_nada(edad, "edad", EDAD_MINIMA_ADMISIBLE, EDAD_MAXIMA_ADMISIBLE)

def exigir_semestre_admisible(semestre: int | None) -> int | None:
    return _entero_o_nada(
        semestre, "semestre", SEMESTRE_MINIMO_ADMISIBLE, SEMESTRE_MAXIMO_ADMISIBLE
    )

@dataclass(frozen=True, slots=True)
class Identidad:

    sujeto_google: str
    correo: str
    nombre: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sujeto_google", _texto_obligatorio(self.sujeto_google, "sujeto_google"))
        correo = _texto_obligatorio(self.correo, "correo").lower()
        if "@" not in correo[1:]:
            raise IdentidadInvalida("correo no tiene la forma de una dirección")
        object.__setattr__(self, "correo", correo)
        object.__setattr__(self, "nombre", (self.nombre or "").strip())

@dataclass(frozen=True, slots=True)
class PerfilOnboarding:

    identidad: Identidad
    edad: int | None = None
    facultad: str = ""
    programa: str = ""
    semestre: int | None = None
    clase_vinculada: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.identidad, Identidad):
            raise IdentidadInvalida("un perfil de onboarding cuelga de una identidad verificada")
        object.__setattr__(
            self,
            "edad",
            _entero_o_nada(self.edad, "edad", EDAD_MINIMA_ADMISIBLE, EDAD_MAXIMA_ADMISIBLE),
        )
        object.__setattr__(
            self,
            "semestre",
            _entero_o_nada(
                self.semestre, "semestre", SEMESTRE_MINIMO_ADMISIBLE, SEMESTRE_MAXIMO_ADMISIBLE
            ),
        )
        facultad = (self.facultad or "").strip()
        programa = (self.programa or "").strip()
        object.__setattr__(self, "facultad", facultad)
        object.__setattr__(self, "programa", programa)

        if facultad and programa:
            from dominio.modelo.oferta_academica import (
                OfertaAcademicaInvalida,
                exigir_oferta_valida,
            )

            try:
                exigir_oferta_valida(facultad, programa)
            except OfertaAcademicaInvalida as error:
                raise IdentidadInvalida(str(error)) from error
        object.__setattr__(self, "clase_vinculada", bool(self.clase_vinculada))

    @property
    def sujeto_google(self) -> str:
        return self.identidad.sujeto_google

    @property
    def categoria_de_edad(self) -> CategoriaDeEdad:
        return categoria_de_edad(self.edad)

    @property
    def es_menor(self) -> bool:
        return self.categoria_de_edad is CategoriaDeEdad.MENOR

    @property
    def completo(self) -> bool:
        return (
            self.edad is not None
            and bool(self.programa)
            and self.semestre is not None
            and self.clase_vinculada
        )

    @property
    def campos_pendientes(self) -> tuple[str, ...]:
        faltan = []
        if self.edad is None:
            faltan.append("edad")
        if not self.programa:
            faltan.append("programa")
        if self.semestre is None:
            faltan.append("semestre")
        if not self.clase_vinculada:
            faltan.append("clase")
        return tuple(faltan)
