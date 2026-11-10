from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Final

from dominio.kpi.definiciones import (
    INTERVALO,
    MUESTRA_MINIMA,
    VERSION_DEFINICIONES,
    ZONA_HORARIA,
)


VERSION_CATALOGO: Final = "kpi.v1.9"


class KPIInvalido(ValueError):
    pass

class EstadoKPI(StrEnum):

    DISPONIBLE = "disponible"

    SIN_DATOS = "sin_datos"

    NO_INSTRUMENTADO = "no_instrumentado"

    MUESTRA_INSUFICIENTE = "muestra_insuficiente"

    DATOS_INCOMPLETOS = "datos_incompletos"

    CALCULO_NO_APLICABLE = "calculo_no_aplicable"

    ERROR_DE_CALIDAD = "error_de_calidad"

class Dimension(StrEnum):

    ADOPCION = "adopcion"
    APRENDIZAJE = "aprendizaje"
    RECUPERACION = "recuperacion"
    SUPERVISION = "supervision"
    CONDUCTUAL = "conductual"
    INSTITUCION = "institucion"

class Unidad(StrEnum):

    PROPORCION = "proporcion"
    CONTEO = "conteo"
    DIAS = "dias"
    HORAS = "horas"
    TURNOS = "turnos"
    PUNTUACION = "puntuacion"

class Instrumentacion(StrEnum):

    DISPONIBLE = "disponible"

    PENDIENTE_PRODUCTOR = "pendiente_productor"

    SIN_INSTRUMENTO = "sin_instrumento"

    EXCLUIDO_POR_DECISION = "excluido_por_decision"

class EstadoTecnico(StrEnum):

    DISPONIBLE = "disponible"
    PENDIENTE_PRODUCTOR = "pendiente_productor"
    SIN_FUENTE = "sin_fuente"
    EXCLUIDO = "excluido"

class MadurezMetodologica(StrEnum):

    OPERACIONAL = "operacional"
    EXPERIMENTAL = "experimental"
    EN_CALIBRACION = "en_calibracion"
    VALIDADO = "validado"
    PROXIMO = "proximo"
    EXCLUIDO = "excluido"

class Alcance(StrEnum):

    DOCENTE = "docente"
    INSTITUCIONAL = "institucional"

@dataclass(frozen=True, slots=True)
class Instrumento:

    nombre: str = ""
    version: str = ""
    constructo: str = ""
    items: tuple[str, ...] = ()
    escala: str = ""
    regla_de_puntuacion: str = ""
    minimo_de_observaciones: int = MUESTRA_MINIMA

    falta: str = ""

    def como_json(self) -> dict:
        return {
            "nombre": self.nombre,
            "version": self.version,
            "constructo": self.constructo,
            "items": list(self.items),
            "escala": self.escala,
            "regla_de_puntuacion": self.regla_de_puntuacion,
            "minimo_de_observaciones": self.minimo_de_observaciones,
            "falta": self.falta,
        }

@dataclass(frozen=True, slots=True)
class DefinicionKPI:

    codigo: str
    nombre: str
    dimension: Dimension
    definicion_operacional: str
    unidad: Unidad
    numerador: str
    denominador: str
    poblacion_elegible: str

    fuentes: tuple[str, ...]
    instrumentacion: Instrumentacion = Instrumentacion.DISPONIBLE
    madurez_metodologica: MadurezMetodologica | None = None

    falta: str = ""
    muestra_minima: int = MUESTRA_MINIMA
    limitaciones: tuple[str, ...] = ()
    alcances: tuple[Alcance, ...] = (Alcance.DOCENTE, Alcance.INSTITUCIONAL)

    depende_de_corpus: bool = False
    depende_de_modelo: bool = False
    instrumento: Instrumento | None = None

    def __post_init__(self) -> None:
        if not self.codigo.startswith(f"{self.dimension.value}."):
            raise KPIInvalido(
                f"el codigo «{self.codigo}» no empieza por su dimension "
                f"«{self.dimension.value}»"
            )
        if self.instrumentacion is not Instrumentacion.DISPONIBLE and not self.falta:
            raise KPIInvalido(f"«{self.codigo}» no esta instrumentado y no dice que falta")
        if self.instrumentacion is Instrumentacion.DISPONIBLE and not self.fuentes:
            raise KPIInvalido(f"«{self.codigo}» se declara instrumentado sin fuentes")

    @property
    def calculable(self) -> bool:
        return self.instrumentacion is Instrumentacion.DISPONIBLE

    @property
    def estado_tecnico(self) -> EstadoTecnico:
        return {
            Instrumentacion.DISPONIBLE: EstadoTecnico.DISPONIBLE,
            Instrumentacion.PENDIENTE_PRODUCTOR: EstadoTecnico.PENDIENTE_PRODUCTOR,
            Instrumentacion.SIN_INSTRUMENTO: EstadoTecnico.SIN_FUENTE,
            Instrumentacion.EXCLUIDO_POR_DECISION: EstadoTecnico.EXCLUIDO,
        }[self.instrumentacion]

    @property
    def madurez(self) -> MadurezMetodologica:
        if self.madurez_metodologica is not None:
            return self.madurez_metodologica
        if self.instrumentacion is Instrumentacion.EXCLUIDO_POR_DECISION:
            return MadurezMetodologica.EXCLUIDO
        if self.instrumentacion is not Instrumentacion.DISPONIBLE:
            return MadurezMetodologica.PROXIMO
        return MadurezMetodologica.OPERACIONAL

    def admite(self, alcance: Alcance) -> bool:
        return alcance in self.alcances

    @property
    def formula(self) -> str:
        from dominio.kpi.instrumentos import PROPUESTAS

        observables = {
            "conductual.ansiedad_matematica": "p_A = m_A / m",
            "aprendizaje.concepciones_dos_niveles": "p_C = (d16 + d21 + d22 + d23) / s",
            "conductual.reiteracion_tras_correccion": "p_S = r / o",
        }
        if self.codigo in observables:
            return observables[self.codigo]

        if self.codigo in PROPUESTAS:
            return PROPUESTAS[self.codigo]["formula"]
        if self.unidad is Unidad.PROPORCION:
            return "numerador / denominador"
        if "distribución" in self.denominador:
            return "mediana(numerador); percentiles P25 y P75 en detalle"
        if self.unidad is Unidad.CONTEO:
            return "conteo(numerador)"
        if self.instrumento is not None:
            return (
                self.instrumento.regla_de_puntuacion
                or "pendiente de la regla de puntuación del instrumento versionado"
            )
        return "numerador / denominador"

    def como_json(self) -> dict:
        from dominio.kpi.metodologia import explicar

        return {
            "codigo": self.codigo,
            "metodologia": explicar(self),
            "version_catalogo": VERSION_CATALOGO,
            "nombre": self.nombre,
            "dimension": self.dimension.value,
            "definicion_operacional": self.definicion_operacional,
            "formula": self.formula,
            "unidad": self.unidad.value,
            "numerador": self.numerador,
            "denominador": self.denominador,

            "definicion_numerador": self.numerador,
            "definicion_denominador": self.denominador,
            "poblacion_elegible": self.poblacion_elegible,
            "fuentes": list(self.fuentes),
            "instrumentacion": self.instrumentacion.value,
            "estado_tecnico": self.estado_tecnico.value,
            "madurez_metodologica": self.madurez.value,
            "falta": self.falta,
            "muestra_minima": self.muestra_minima,
            "limitaciones": list(self.limitaciones),
            "alcances": [alcance.value for alcance in self.alcances],
            "depende_de_corpus": self.depende_de_corpus,
            "depende_de_modelo": self.depende_de_modelo,
            "instrumento": self.instrumento.como_json() if self.instrumento else None,
        }

@dataclass(frozen=True, slots=True)
class Periodo:

    desde: datetime
    hasta: datetime
    zona_horaria: str = ZONA_HORARIA
    intervalo: str = INTERVALO

    def __post_init__(self) -> None:
        if self.desde.tzinfo is None or self.hasta.tzinfo is None:
            raise KPIInvalido("un periodo sin zona horaria no es un instante inequivoco")
        if self.desde >= self.hasta:
            raise KPIInvalido("el periodo termina antes de empezar")

    def como_json(self) -> dict:
        return {
            "desde": self.desde.isoformat(),
            "hasta": self.hasta.isoformat(),
            "zona_horaria": self.zona_horaria,
            "intervalo": self.intervalo,
        }

@dataclass(frozen=True, slots=True)
class ContextoDeCalculo:

    periodo: Periodo
    calculado_en: datetime
    filtros: dict = field(default_factory=dict)
    version_corpus: str = ""
    version_modelo: str = ""
    versiones_corpus: tuple[str, ...] = ()
    versiones_modelo: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class Medicion:

    valor: float | None = None
    numerador: float | None = None
    denominador: float | None = None
    muestra: int = 0
    faltantes: int = 0
    advertencias: tuple[str, ...] = ()

    detalle: dict = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ResultadoKPI:

    definicion: DefinicionKPI
    contexto: ContextoDeCalculo
    estado: EstadoKPI
    medicion: Medicion
    interpretacion: str
    version_interpretacion: str
    limitaciones: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _exigir_coherencia(self)

    def como_json(self) -> dict:
        base = self.definicion.como_json()
        base.update(
            {
                "version_definiciones": VERSION_DEFINICIONES,
                "estado": self.estado.value,
                "valor": self.medicion.valor,
                "unidad": self.definicion.unidad.value,
                "numerador": self.medicion.numerador,
                "denominador": self.medicion.denominador,
                "muestra": self.medicion.muestra,
                "faltantes": self.medicion.faltantes,
                "detalle": dict(self.medicion.detalle),
                "advertencias": list(self.medicion.advertencias),
                "periodo": self.contexto.periodo.como_json(),
                "filtros": dict(self.contexto.filtros),
                "calculado_en": self.contexto.calculado_en.isoformat(),
                "version_corpus": self.contexto.version_corpus,
                "version_modelo": self.contexto.version_modelo,
                "versiones_corpus": list(self.contexto.versiones_corpus),
                "versiones_modelo": list(self.contexto.versiones_modelo),
                "interpretacion": self.interpretacion,
                "version_interpretacion": self.version_interpretacion,
                "limitaciones": list(self.limitaciones),
            }
        )
        return base

def _exigir_coherencia(resultado: ResultadoKPI) -> None:
    medicion = resultado.medicion
    if resultado.estado is EstadoKPI.DISPONIBLE:
        if medicion.valor is None:
            raise KPIInvalido(f"«{resultado.definicion.codigo}» se declara disponible sin valor")
        return
    if medicion.valor is not None:
        raise KPIInvalido(
            f"«{resultado.definicion.codigo}» lleva valor con estado "
            f"«{resultado.estado.value}»: un numero ahi se leeria como medida"
        )
