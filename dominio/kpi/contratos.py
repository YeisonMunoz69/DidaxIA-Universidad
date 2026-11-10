"""
contratos.py — Los tipos del catálogo KPI v1.3 y del resultado explicable
==========================================================================

Dos contratos, y ninguno es «un diccionario con cifras».

**`DefinicionKPI`** es lo que el catálogo declara ANTES de mirar la base: código
estable, dimensión, fórmula, población, fuentes, estado de instrumentación,
muestra mínima y limitaciones conocidas. Existe aunque nadie la calcule nunca.

**`ResultadoKPI`** es lo que una lectura devuelve. Lleva la definición entera
dentro, más el periodo, los filtros aplicados, el estado, el valor con su
numerador y su denominador, la muestra, los faltantes, las advertencias, la
interpretación determinista y las limitaciones.

Las tres reglas duras
-------------------------
1. **Un valor sólo existe si el estado es `DISPONIBLE`.** Los otros seis
   estados dejan `valor` en `None`. Un cero significa «se midió y dio cero», y
   nunca «no hay datos», «no está instrumentado» o «la muestra se suprimió».
   `_exigir_coherencia()` lo impone en el constructor: no es una convención que
   alguien deba recordar.
2. **No se divide por cero.** La fábrica `proporcion()` de `medidas.py` devuelve
   `SIN_DATOS` cuando el denominador es cero, y no un `0.0` que parecería un
   resultado.
3. **La interpretación es determinista y versionada.** La produce
   `dominio/kpi/interpretacion.py` a partir del estado y de las cifras; ningún
   modelo de lenguaje la escribe. Ver el motivo en ese módulo.

Por qué el resultado lleva su propia definición dentro
-----------------------------------------------------------
Porque el consumidor —hoy una ruta HTTP, mañana un informe— tiene que poder
explicar una cifra sin volver a consultar el catálogo, y porque un resultado
guardado o exportado envejece: si sólo llevara el código, releerlo dentro de
seis meses lo interpretaría con la definición de entonces y no con la que lo
produjo.


"""

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

#: La versión del catálogo. Sube cuando cambia un código, una fórmula o una
#: población; no cuando cambia el SQL que la calcula.
VERSION_CATALOGO: Final = "kpi.v1.9"


class KPIInvalido(ValueError):
    """Un resultado que se contradice a sí mismo. Nunca se construye."""


class EstadoKPI(StrEnum):
    """Los siete estados exactos que el encargo de la Fase 8 enumera.

    No hay un octavo, y ninguno es opcional: un indicador que no se pueda
    publicar tiene que decir **por cuál de estas siete razones**, porque cada
    una se corrige de una forma distinta.
    """

    #: Se calculó con datos suficientes. Es el único estado con `valor`.
    DISPONIBLE = "disponible"
    #: El instrumento existe y la consulta corrió, pero no hubo observaciones.
    SIN_DATOS = "sin_datos"
    #: Nadie produce todavía el dato que este indicador necesita.
    NO_INSTRUMENTADO = "no_instrumentado"
    #: Hubo observaciones, pero por debajo del mínimo publicable.
    MUESTRA_INSUFICIENTE = "muestra_insuficiente"
    #: Se calculó sobre una base con huecos conocidos; el valor no se publica.
    DATOS_INCOMPLETOS = "datos_incompletos"
    #: El indicador no aplica a este alcance o una decisión vigente lo excluye.
    CALCULO_NO_APLICABLE = "calculo_no_aplicable"
    #: Los datos existen pero se contradicen; publicar el valor sería afirmar
    #: algo que la propia base desmiente.
    ERROR_DE_CALIDAD = "error_de_calidad"


class Dimension(StrEnum):
    """Las seis dimensiones del catálogo v1.1. El código de cada KPI empieza
    por la suya, de modo que el prefijo baste para agrupar sin una tabla."""

    ADOPCION = "adopcion"
    APRENDIZAJE = "aprendizaje"
    RECUPERACION = "recuperacion"
    SUPERVISION = "supervision"
    CONDUCTUAL = "conductual"
    INSTITUCION = "institucion"


class Unidad(StrEnum):
    """En qué se expresa el valor. Sin esto, `0.42` no dice si son horas,
    turnos o una proporción, y una gráfica lo pintaría igual."""

    PROPORCION = "proporcion"
    CONTEO = "conteo"
    DIAS = "dias"
    HORAS = "horas"
    TURNOS = "turnos"
    PUNTUACION = "puntuacion"


class Instrumentacion(StrEnum):
    """Si el dato que este indicador necesita **se produce hoy**.

    Es la diferencia entre «no hay actividad» y «nadie está midiendo», y el
    encargo pide distinguirlas sin ambigüedad.
    """

    #: Hay un productor real y verificable en el código de hoy.
    DISPONIBLE = "disponible"
    #: El contrato de evento existe y está validado, pero quien lo emite es la
    #: interfaz y esa parte todavía no se implementó.
    PENDIENTE_PRODUCTOR = "pendiente_productor"
    #: Hace falta una rúbrica, un ítem o un instrumento aprobado por el equipo.
    #: No se suple con inferencia sobre texto libre.
    SIN_INSTRUMENTO = "sin_instrumento"
    #: Una decisión vigente excluye su población de todo KPI (`EQ-031`).
    EXCLUIDO_POR_DECISION = "excluido_por_decision"


class EstadoTecnico(StrEnum):
    """Disponibilidad de la fuente y de su productor, no validez científica."""

    DISPONIBLE = "disponible"
    PENDIENTE_PRODUCTOR = "pendiente_productor"
    SIN_FUENTE = "sin_fuente"
    EXCLUIDO = "excluido"


class MadurezMetodologica(StrEnum):
    """Qué puede afirmarse del método aunque técnicamente produzca un valor."""

    OPERACIONAL = "operacional"
    EXPERIMENTAL = "experimental"
    EN_CALIBRACION = "en_calibracion"
    VALIDADO = "validado"
    PROXIMO = "proximo"
    EXCLUIDO = "excluido"


class Alcance(StrEnum):
    """Quién puede pedir el indicador. `DOCENTE` implica «sólo sus clases»."""

    DOCENTE = "docente"
    INSTITUCIONAL = "institucional"


@dataclass(frozen=True, slots=True)
class Instrumento:
    """La ficha metodológica de un indicador conductual o afectivo.

    El encargo es explícito: estos indicadores *«no son diagnósticos
    clínicos»*. Un número sin instrumento, versión, constructo, escala y regla
    de puntuación no es una medida psicométrica: es una opinión con decimales.
    Por eso el catálogo lleva esta ficha aunque hoy esté vacía en casi todos —
    declarar el hueco es lo que impide llenarlo por inferencia.
    """

    nombre: str = ""
    version: str = ""
    constructo: str = ""
    items: tuple[str, ...] = ()
    escala: str = ""
    regla_de_puntuacion: str = ""
    minimo_de_observaciones: int = MUESTRA_MINIMA
    #: Qué falta exactamente para que deje de ser `SIN_INSTRUMENTO`.
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
    """Una entrada del catálogo. Estable, versionada y probada."""

    codigo: str
    nombre: str
    dimension: Dimension
    definicion_operacional: str
    unidad: Unidad
    numerador: str
    denominador: str
    poblacion_elegible: str
    #: Tablas o vistas de origen. Es lo que permite auditar una cifra sin leer
    #: el adaptador, y lo que dice a qué alcanza una supresión.
    fuentes: tuple[str, ...]
    instrumentacion: Instrumentacion = Instrumentacion.DISPONIBLE
    madurez_metodologica: MadurezMetodologica | None = None
    #: Por qué no está instrumentado, con nombre propio. Vacío si lo está.
    falta: str = ""
    muestra_minima: int = MUESTRA_MINIMA
    limitaciones: tuple[str, ...] = ()
    alcances: tuple[Alcance, ...] = (Alcance.DOCENTE, Alcance.INSTITUCIONAL)
    #: Si el resultado tiene que declarar versión de corpus o de modelo.
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
        """Si hoy existe un productor del dato. No promete que haya filas."""
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
        """Expresión publicable y estable, sin deducir una ausencia como cero.

        El catálogo ya distingue razones, recuentos, distribuciones e
        instrumentos. La fórmula se deriva de esa tipología cerrada y conserva
        los nombres operacionales de numerador y denominador; no intenta
        reconstruirla desde el valor observado.
        """
        from dominio.kpi.instrumentos import PROPUESTAS  # noqa: PLC0415

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
        from dominio.kpi.metodologia import explicar  # noqa: PLC0415

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
            # En un resultado, `numerador` y `denominador` pasan a ser las
            # cifras observadas. Estos dos nombres conservan la definición que
            # las explica; así el informe no pierde el contrato al añadir el
            # valor medido.
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
    """El intervalo consultado, y la zona en la que se interpreta.

    `desde` y `hasta` son instantes con zona y se persisten así. `ZONA_HORARIA`
    no los mueve: decide a qué **fecha local** pertenece cada uno cuando el
    indicador cuenta días.
    """

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
    """Lo que rodea a una medición y es igual para todos los KPI de una lectura.

    Va aparte de `Medicion` porque no lo decide el indicador: lo decide quien
    pregunta —el periodo y los filtros— y el sistema —las versiones y el
    instante de cálculo—.
    """

    periodo: Periodo
    calculado_en: datetime
    filtros: dict = field(default_factory=dict)
    version_corpus: str = ""
    version_modelo: str = ""
    versiones_corpus: tuple[str, ...] = ()
    versiones_modelo: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Medicion:
    """Las cifras de un indicador. Todo `None` u opcional a propósito: un
    estado distinto de `DISPONIBLE` no trae ninguna."""

    valor: float | None = None
    numerador: float | None = None
    denominador: float | None = None
    muestra: int = 0
    faltantes: int = 0
    advertencias: tuple[str, ...] = ()
    #: Percentiles y otros acompañantes de una distribución, con nombre.
    detalle: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResultadoKPI:
    """Una cifra que se puede explicar entera sin salir de ella."""

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
    """Las dos mitades de la primera regla dura, impuestas en la construcción.

    Va aquí y no en cada llamador porque un invariante que depende de la
    disciplina del llamador se rompe en la llamada número cuarenta.
    """
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
