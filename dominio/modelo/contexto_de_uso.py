from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


ROL_ESTUDIANTE = "estudiante"


ROLES_PROFESIONALES = frozenset({"docente", "investigador"})


class ContextoDeUso(StrEnum):

    APRENDIZAJE_ESTUDIANTE = "aprendizaje_estudiante"

    CONSULTA_PROFESIONAL = "consulta_profesional"

    TUTORIA_ACADEMICA_SIN_INVESTIGACION = "tutoria_academica_sin_investigacion"

CONTEXTO_HISTORICO = ContextoDeUso.APRENDIZAJE_ESTUDIANTE


def contexto_de_uso_de(rol: str | None) -> ContextoDeUso:
    return (
        ContextoDeUso.APRENDIZAJE_ESTUDIANTE
        if rol == ROL_ESTUDIANTE
        else ContextoDeUso.CONSULTA_PROFESIONAL
    )

def es_consulta_profesional(contexto: ContextoDeUso) -> bool:
    return contexto is ContextoDeUso.CONSULTA_PROFESIONAL

def alimenta_evaluacion(contexto: ContextoDeUso) -> bool:
    return contexto is ContextoDeUso.APRENDIZAJE_ESTUDIANTE

def puede_consultar_como_profesional(rol: str | None) -> bool:
    return rol in ROLES_PROFESIONALES

@dataclass(frozen=True, slots=True)
class PoliticaDelTurno:

    contexto: ContextoDeUso

    @classmethod
    def de_la_sesion(cls, rol: str | None) -> PoliticaDelTurno:
        return cls(contexto_de_uso_de(rol))

    @classmethod
    def del_contexto(cls, contexto: ContextoDeUso | str) -> PoliticaDelTurno:
        return cls(ContextoDeUso(contexto))

    @property
    def es_consulta_profesional(self) -> bool:
        return es_consulta_profesional(self.contexto)

    @property
    def resuelve_matricula(self) -> bool:
        return alimenta_evaluacion(self.contexto)

    @property
    def escribe_perfil_longitudinal(self) -> bool:
        return alimenta_evaluacion(self.contexto)

    @property
    def extrae_indicadores_conductuales(self) -> bool:
        return alimenta_evaluacion(self.contexto)

    @property
    def diagnostica(self) -> bool:
        return alimenta_evaluacion(self.contexto)

    @property
    def encola_supervision(self) -> bool:
        return alimenta_evaluacion(self.contexto)

    @property
    def cuenta_en_agregados(self) -> bool:
        return alimenta_evaluacion(self.contexto)
