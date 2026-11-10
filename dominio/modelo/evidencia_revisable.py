from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from dominio.modelo.menores import TIPO_MIME_ESPERADO, ResultadoDeRevision


LIMITE_MINIMO = 1
LIMITE_MAXIMO = 100
LIMITE_POR_DEFECTO = 20


class ConsultaInvalida(ValueError):
    pass

class EstadoDeEvidencia(StrEnum):

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"

class FiltroDeEvidencias(StrEnum):

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    TODOS = "todos"

FILTRO_POR_DEFECTO = FiltroDeEvidencias.PENDIENTE


def filtro_desde(valor: object) -> FiltroDeEvidencias:
    if valor is None:
        return FILTRO_POR_DEFECTO
    texto = str(valor).strip().lower()
    if not texto:
        return FILTRO_POR_DEFECTO
    try:
        return FiltroDeEvidencias(texto)
    except ValueError:
        admitidos = ", ".join(f.value for f in FiltroDeEvidencias)
        raise ConsultaInvalida(f"estado no admitido; los admitidos son: {admitidos}") from None

def limite_desde(valor: object) -> int:
    if valor is None:
        return LIMITE_POR_DEFECTO
    if isinstance(valor, bool):
        raise ConsultaInvalida("límite tiene que ser un número entero")
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return LIMITE_POR_DEFECTO
        if not texto.isdigit():
            raise ConsultaInvalida("límite tiene que ser un número entero")
        valor = int(texto)
    if not isinstance(valor, int):
        raise ConsultaInvalida("límite tiene que ser un número entero")
    if not LIMITE_MINIMO <= valor <= LIMITE_MAXIMO:
        raise ConsultaInvalida(
            f"límite tiene que estar entre {LIMITE_MINIMO} y {LIMITE_MAXIMO}"
        )
    return valor

@dataclass(frozen=True, slots=True)
class PosicionDeCursor:

    recibido_en: datetime
    evidencia: int

    def __post_init__(self) -> None:
        if not isinstance(self.recibido_en, datetime):
            raise ConsultaInvalida("la posición del cursor lleva una fecha")
        if self.recibido_en.tzinfo is None:

            raise ConsultaInvalida("la posición del cursor lleva una fecha con zona")
        if isinstance(self.evidencia, bool) or not isinstance(self.evidencia, int):
            raise ConsultaInvalida("la posición del cursor lleva un identificador")
        if self.evidencia < 1:
            raise ConsultaInvalida("la posición del cursor lleva un identificador")

    def codificar(self) -> str:
        crudo = f"{self.recibido_en.isoformat()}|{self.evidencia}".encode()
        return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")

    @classmethod
    def descodificar(cls, texto: str) -> PosicionDeCursor:
        if not isinstance(texto, str) or not texto.strip():
            raise ConsultaInvalida("cursor no válido")
        crudo = texto.strip()
        relleno = "=" * (-len(crudo) % 4)
        try:
            plano = base64.urlsafe_b64decode(crudo + relleno).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            raise ConsultaInvalida("cursor no válido") from None
        fecha, separador, identificador = plano.partition("|")
        if not separador or not identificador.isdigit():
            raise ConsultaInvalida("cursor no válido") from None
        try:
            momento = datetime.fromisoformat(fecha)
        except ValueError:
            raise ConsultaInvalida("cursor no válido") from None
        try:
            return cls(recibido_en=momento, evidencia=int(identificador))
        except ConsultaInvalida:

            raise ConsultaInvalida("cursor no válido") from None

def cursor_desde(valor: object) -> PosicionDeCursor | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return PosicionDeCursor.descodificar(texto)

@dataclass(frozen=True, slots=True)
class EvidenciaRevisable:

    evidencia: int
    sujeto_google: str
    intento: int
    version: str
    sha256: str
    tamano_bytes: int
    recibido_en: datetime
    tipo_mime: str = TIPO_MIME_ESPERADO

    resultado: ResultadoDeRevision | None = None
    revisada_en: datetime | None = None

    motivo: str = ""

    estudiante_nombre: str = ""
    clases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self._exigir_textos()
        self._exigir_cuentas()
        if not isinstance(self.recibido_en, datetime):
            raise ConsultaInvalida("una evidencia conserva cuándo se recibió")
        self._exigir_revision_completa()

    def _exigir_textos(self) -> None:
        for campo in ("sujeto_google", "version", "sha256"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ConsultaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())

    def _exigir_cuentas(self) -> None:
        for campo, motivo in (
            ("evidencia", "el identificador de la evidencia es un entero positivo"),
            ("intento", "el número de intento empieza en 1"),
            ("tamano_bytes", "el tamaño es un número de bytes"),
        ):
            valor = getattr(self, campo)
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
                raise ConsultaInvalida(motivo)

    def _exigir_revision_completa(self) -> None:
        if self.resultado is not None:
            object.__setattr__(self, "resultado", ResultadoDeRevision(self.resultado))
        if (self.resultado is None) != (self.revisada_en is None):
            raise ConsultaInvalida("una revisión lleva resultado y fecha, o no se registra")
        if self.revisada_en is not None and not isinstance(self.revisada_en, datetime):
            raise ConsultaInvalida("revisada_en tiene que ser una fecha")
        motivo = (self.motivo or "").strip()
        if motivo and self.resultado is None:

            raise ConsultaInvalida("un motivo sin revisión no explica ninguna decisión")
        object.__setattr__(self, "motivo", motivo)
        object.__setattr__(self, "estudiante_nombre", (self.estudiante_nombre or "").strip())
        object.__setattr__(
            self,
            "clases",
            tuple(nombre.strip() for nombre in self.clases if isinstance(nombre, str) and nombre.strip()),
        )

    @property
    def estado(self) -> EstadoDeEvidencia:
        if self.resultado is None:
            return EstadoDeEvidencia.PENDIENTE
        if self.resultado is ResultadoDeRevision.APROBADA:
            return EstadoDeEvidencia.APROBADA
        return EstadoDeEvidencia.RECHAZADA

    @property
    def posicion(self) -> PosicionDeCursor:
        return PosicionDeCursor(recibido_en=self.recibido_en, evidencia=self.evidencia)

@dataclass(frozen=True, slots=True)
class PaginaDeEvidencias:

    evidencias: tuple[EvidenciaRevisable, ...] = ()
    cursor_siguiente: str | None = None

    @property
    def hay_mas(self) -> bool:
        return self.cursor_siguiente is not None
