from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.puertos.almacen import TransicionInvalida


class ConsentimientoInvalido(ValueError):
    pass

class EstadoConsentimiento(StrEnum):

    PENDIENTE = "pendiente"
    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"
    REVOCADO = "revocado"

ESTADOS_REGISTRABLES: frozenset[EstadoConsentimiento] = frozenset(
    {
        EstadoConsentimiento.OTORGADO,
        EstadoConsentimiento.RECHAZADO,
        EstadoConsentimiento.REVOCADO,
    }
)


class Finalidad(StrEnum):

    AUTENTICACION_Y_SEGURIDAD = "autenticacion_y_seguridad"
    HISTORIAL_CONVERSACIONAL = "historial_conversacional"
    PERFIL_CONDUCTUAL = "perfil_conductual"
    PERSONALIZACION_PEDAGOGICA = "personalizacion_pedagogica"
    INVESTIGACION = "investigacion"
    VISUALIZACION_DOCENTE = "visualizacion_docente"

FINALIDADES_OBLIGATORIAS: frozenset[Finalidad] = frozenset(Finalidad)


class Alcance(StrEnum):

    TITULAR = "titular"
    ASENTIMIENTO = "asentimiento"
    REPRESENTANTE = "representante"

TRANSICIONES: dict[EstadoConsentimiento, frozenset[EstadoConsentimiento]] = {
    EstadoConsentimiento.PENDIENTE: frozenset(
        {EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO}
    ),
    EstadoConsentimiento.OTORGADO: frozenset({EstadoConsentimiento.REVOCADO}),
    EstadoConsentimiento.RECHAZADO: frozenset({EstadoConsentimiento.OTORGADO}),
    EstadoConsentimiento.REVOCADO: frozenset({EstadoConsentimiento.OTORGADO}),
}


def transicion_admitida(
    desde: EstadoConsentimiento,
    hacia: EstadoConsentimiento,
    *,
    cambia_version: bool = False,
    cambia_categoria: bool = False,
) -> bool:

    if hacia not in ESTADOS_REGISTRABLES:
        return False
    if hacia in TRANSICIONES[desde]:
        return True
    return (
        (cambia_version or cambia_categoria)
        and desde in (EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO)
        and hacia in (EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO)
    )

def exigir_transicion(
    desde: EstadoConsentimiento,
    hacia: EstadoConsentimiento,
    *,
    cambia_version: bool = False,
    cambia_categoria: bool = False,
) -> None:

    if not transicion_admitida(
        desde, hacia, cambia_version=cambia_version, cambia_categoria=cambia_categoria
    ):
        motivo = (
            ""
            if cambia_version or cambia_categoria
            else " sin un cambio de versión ni de categoría de edad"
        )
        raise TransicionInvalida(
            f"el consentimiento no puede pasar de {desde.value!r} a {hacia.value!r}{motivo}"
        )

def _huella_valida(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not SHA256.fullmatch(valor):
        raise ConsentimientoInvalido(f"{campo} tiene que ser un SHA-256 en minúsculas")
    return valor

def _codigo_valido(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ConsentimientoInvalido(f"{campo} no puede quedar vacío")
    return valor.strip()

@dataclass(frozen=True, slots=True)
class VersionDeConsentimiento:

    codigo: str
    alcance: Alcance
    finalidades: frozenset[Finalidad]
    huella_contenido: str
    vigente_desde: datetime
    vigente_hasta: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", _codigo_valido(self.codigo, "codigo"))
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        finalidades = frozenset(Finalidad(f) for f in self.finalidades)
        faltan = FINALIDADES_OBLIGATORIAS - finalidades
        if faltan:

            raise ConsentimientoInvalido(
                "una versión publicada tiene que cubrir todas las finalidades "
                f"obligatorias; faltan {sorted(f.value for f in faltan)}"
            )
        object.__setattr__(self, "finalidades", finalidades)
        object.__setattr__(
            self, "huella_contenido", _huella_valida(self.huella_contenido, "huella_contenido")
        )
        if not isinstance(self.vigente_desde, datetime):
            raise ConsentimientoInvalido("vigente_desde tiene que ser una fecha")
        if self.vigente_hasta is not None and self.vigente_hasta <= self.vigente_desde:
            raise ConsentimientoInvalido("vigente_hasta tiene que ser posterior a vigente_desde")

    def vigente_en(self, momento: datetime) -> bool:
        if momento < self.vigente_desde:
            return False
        return self.vigente_hasta is None or momento < self.vigente_hasta

@dataclass(frozen=True, slots=True)
class EventoConsentimiento:

    sujeto_google: str
    version: str
    estado: EstadoConsentimiento
    comprobante: str
    momento: datetime
    secuencia: int = 0

    categoria_edad: CategoriaDeEdad | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "sujeto_google", _codigo_valido(self.sujeto_google, "sujeto_google"))
        object.__setattr__(self, "version", _codigo_valido(self.version, "version"))
        if self.categoria_edad is not None:
            categoria = CategoriaDeEdad(self.categoria_edad)
            if categoria is CategoriaDeEdad.NO_DECLARADA:
                raise ConsentimientoInvalido(
                    "no se registra consentimiento sin edad declarada"
                )
            object.__setattr__(self, "categoria_edad", categoria)
        estado = EstadoConsentimiento(self.estado)
        if estado not in ESTADOS_REGISTRABLES:
            raise ConsentimientoInvalido(
                f"{estado.value!r} no es un acto: sólo se registran "
                f"{sorted(e.value for e in ESTADOS_REGISTRABLES)}"
            )
        object.__setattr__(self, "estado", estado)
        object.__setattr__(self, "comprobante", _huella_valida(self.comprobante, "comprobante"))
        if not isinstance(self.momento, datetime):
            raise ConsentimientoInvalido("momento tiene que ser una fecha")

@dataclass(frozen=True, slots=True)
class HistorialDeConsentimiento:

    sujeto_google: str
    eventos: tuple[EventoConsentimiento, ...] = field(default_factory=tuple)

    @property
    def ultimo(self) -> EventoConsentimiento | None:
        return self.eventos[-1] if self.eventos else None

    @property
    def estado(self) -> EstadoConsentimiento:
        ultimo = self.ultimo
        return ultimo.estado if ultimo is not None else EstadoConsentimiento.PENDIENTE

    @property
    def version_vigente(self) -> str | None:
        ultimo = self.ultimo
        return ultimo.version if ultimo is not None else None

    @property
    def categoria_edad_vigente(self) -> CategoriaDeEdad | None:
        ultimo = self.ultimo
        return ultimo.categoria_edad if ultimo is not None else None
