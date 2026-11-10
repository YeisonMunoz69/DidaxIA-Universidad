from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.puertos.almacen import TransicionInvalida

_ENLACE = re.compile(r"^https?://", re.IGNORECASE)


TIPO_MIME_ESPERADO = "application/pdf"
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024


PLAZO_REPRESENTANTE_DIAS = 7


class EvidenciaInvalida(ValueError):
    pass

class EstadoAsentimiento(StrEnum):

    NO_REQUERIDO = "no_requerido"
    PENDIENTE = "pendiente"
    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"
    REVOCADO = "revocado"

ESTADOS_ASENTIMIENTO_REGISTRABLES: frozenset[EstadoAsentimiento] = frozenset(
    {
        EstadoAsentimiento.OTORGADO,
        EstadoAsentimiento.RECHAZADO,
        EstadoAsentimiento.REVOCADO,
    }
)


class EstadoRepresentante(StrEnum):

    NO_REQUERIDO = "no_requerido"
    PENDIENTE_DOCUMENTO = "pendiente_documento"
    DOCUMENTO_RECIBIDO = "documento_recibido"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    VENCIDO = "vencido"

class ResultadoDeRevision(StrEnum):

    APROBADA = "aprobada"
    RECHAZADA = "rechazada"

TRANSICIONES_ASENTIMIENTO: dict[EstadoAsentimiento, frozenset[EstadoAsentimiento]] = {

    EstadoAsentimiento.NO_REQUERIDO: frozenset(),
    EstadoAsentimiento.PENDIENTE: frozenset(
        {EstadoAsentimiento.OTORGADO, EstadoAsentimiento.RECHAZADO}
    ),
    EstadoAsentimiento.OTORGADO: frozenset({EstadoAsentimiento.REVOCADO}),
    EstadoAsentimiento.RECHAZADO: frozenset({EstadoAsentimiento.OTORGADO}),
    EstadoAsentimiento.REVOCADO: frozenset({EstadoAsentimiento.OTORGADO}),
}


TRANSICIONES_REPRESENTANTE: dict[EstadoRepresentante, frozenset[EstadoRepresentante]] = {
    EstadoRepresentante.NO_REQUERIDO: frozenset({EstadoRepresentante.PENDIENTE_DOCUMENTO}),
    EstadoRepresentante.PENDIENTE_DOCUMENTO: frozenset(
        {EstadoRepresentante.DOCUMENTO_RECIBIDO, EstadoRepresentante.VENCIDO}
    ),
    EstadoRepresentante.DOCUMENTO_RECIBIDO: frozenset(
        {EstadoRepresentante.APROBADO, EstadoRepresentante.RECHAZADO}
    ),

    EstadoRepresentante.APROBADO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
    EstadoRepresentante.RECHAZADO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
    EstadoRepresentante.VENCIDO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
}


def transicion_asentimiento_admitida(
    desde: EstadoAsentimiento, hacia: EstadoAsentimiento
) -> bool:
    if hacia not in ESTADOS_ASENTIMIENTO_REGISTRABLES:
        return False
    return hacia in TRANSICIONES_ASENTIMIENTO[desde]

def exigir_transicion_asentimiento(
    desde: EstadoAsentimiento, hacia: EstadoAsentimiento
) -> None:
    if not transicion_asentimiento_admitida(desde, hacia):
        raise TransicionInvalida(
            f"el asentimiento no puede pasar de {desde.value!r} a {hacia.value!r}"
        )

def exigir_transicion_representante(
    desde: EstadoRepresentante, hacia: EstadoRepresentante
) -> None:
    if hacia not in TRANSICIONES_REPRESENTANTE[desde]:
        raise TransicionInvalida(
            f"la autorización del representante no puede pasar de "
            f"{desde.value!r} a {hacia.value!r}"
        )

def fecha_limite(desde: datetime, dias: int = PLAZO_REPRESENTANTE_DIAS) -> datetime:
    return desde + timedelta(days=dias)

@dataclass(frozen=True, slots=True)
class EventoAsentimiento:

    sujeto_google: str
    version: str
    estado: EstadoAsentimiento
    comprobante: str
    momento: datetime
    secuencia: int = 0

    def __post_init__(self) -> None:
        for campo in ("sujeto_google", "version"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise EvidenciaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())
        estado = EstadoAsentimiento(self.estado)
        if estado not in ESTADOS_ASENTIMIENTO_REGISTRABLES:
            raise EvidenciaInvalida(f"{estado.value!r} no es un acto de asentimiento")
        object.__setattr__(self, "estado", estado)
        if not SHA256.fullmatch(self.comprobante or ""):
            raise EvidenciaInvalida("comprobante tiene que ser un SHA-256 en minúsculas")
        if not isinstance(self.momento, datetime):
            raise EvidenciaInvalida("momento tiene que ser una fecha")

@dataclass(frozen=True, slots=True)
class HistorialDeAsentimiento:

    sujeto_google: str
    requerido: bool
    eventos: tuple[EventoAsentimiento, ...] = field(default_factory=tuple)

    @property
    def ultimo(self) -> EventoAsentimiento | None:
        return self.eventos[-1] if self.eventos else None

    @property
    def estado(self) -> EstadoAsentimiento:
        if not self.requerido:
            return EstadoAsentimiento.NO_REQUERIDO
        ultimo = self.ultimo
        return ultimo.estado if ultimo is not None else EstadoAsentimiento.PENDIENTE

    @property
    def version_vigente(self) -> str | None:
        if not self.requerido:
            return None
        ultimo = self.ultimo
        return ultimo.version if ultimo is not None else None

@dataclass(frozen=True, slots=True)
class RevisionDeEvidencia:

    resultado: ResultadoDeRevision
    revisada_por: str
    revisada_en: datetime
    motivo: str = ""
    secuencia: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "resultado", ResultadoDeRevision(self.resultado))
        if not isinstance(self.revisada_por, str) or not self.revisada_por.strip():
            raise EvidenciaInvalida("una revisión conserva quién la realizó")
        object.__setattr__(self, "revisada_por", self.revisada_por.strip())
        if not isinstance(self.revisada_en, datetime):
            raise EvidenciaInvalida("una revisión conserva cuándo se realizó")
        motivo = (self.motivo or "").strip()
        if self.resultado is ResultadoDeRevision.RECHAZADA and not motivo:
            raise EvidenciaInvalida("un rechazo exige un motivo comprensible")
        object.__setattr__(self, "motivo", motivo)

@dataclass(frozen=True, slots=True)
class IntentoDeEvidencia:

    sujeto_google: str
    intento: int

    version: str
    referencia: str
    sha256: str
    tamano_bytes: int
    tipo_mime: str = TIPO_MIME_ESPERADO
    recibido_en: datetime | None = None
    revision: RevisionDeEvidencia | None = None
    secuencia: int = 0

    def __post_init__(self) -> None:
        for campo in ("sujeto_google", "version"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise EvidenciaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())
        if isinstance(self.intento, bool) or not isinstance(self.intento, int) or self.intento < 1:
            raise EvidenciaInvalida("el número de intento empieza en 1")
        referencia = (self.referencia or "").strip()
        if not referencia:
            raise EvidenciaInvalida("una evidencia sin referencia no se puede recuperar")
        if _ENLACE.match(referencia):
            raise EvidenciaInvalida(
                "la referencia no puede ser un enlace http(s): EQ-021 descarta un "
                "enlace mutable como evidencia definitiva"
            )
        object.__setattr__(self, "referencia", referencia)
        if not SHA256.fullmatch(self.sha256 or ""):
            raise EvidenciaInvalida("sha256 tiene que ser un SHA-256 en minúsculas")
        if self.tipo_mime != TIPO_MIME_ESPERADO:
            raise EvidenciaInvalida(f"la evidencia se recibe como {TIPO_MIME_ESPERADO}")
        if (
            isinstance(self.tamano_bytes, bool)
            or not isinstance(self.tamano_bytes, int)
            or not 0 < self.tamano_bytes <= TAMANO_MAXIMO_BYTES
        ):
            raise EvidenciaInvalida(
                f"el tamaño tiene que estar entre 1 y {TAMANO_MAXIMO_BYTES} bytes"
            )

def estado_representante(
    intentos: tuple[IntentoDeEvidencia, ...],
    *,
    requerido: bool,
    version_requerida: str | None = None,
    limite: datetime | None = None,
    ahora: datetime | None = None,
) -> EstadoRepresentante:

    if not requerido:
        return EstadoRepresentante.NO_REQUERIDO
    if version_requerida is None:
        return EstadoRepresentante.PENDIENTE_DOCUMENTO
    de_la_version = tuple(i for i in intentos if i.version == version_requerida)
    if not de_la_version:
        if limite is not None and ahora is not None and ahora > limite:
            return EstadoRepresentante.VENCIDO
        return EstadoRepresentante.PENDIENTE_DOCUMENTO
    ultimo = max(de_la_version, key=lambda intento: intento.intento)
    if ultimo.revision is None:
        return EstadoRepresentante.DOCUMENTO_RECIBIDO
    if ultimo.revision.resultado is ResultadoDeRevision.APROBADA:
        return EstadoRepresentante.APROBADO
    return EstadoRepresentante.RECHAZADO
