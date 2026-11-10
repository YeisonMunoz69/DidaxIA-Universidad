from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from dominio.modelo.consentimiento import (
    FINALIDADES_OBLIGATORIAS,
    Alcance,
    ConsentimientoInvalido,
    Finalidad,
)


MEDIO_MARKDOWN = "text/markdown"

MEDIOS_ADMITIDOS = (MEDIO_MARKDOWN,)


LIMITE_BYTES = 512 * 1024


def canonicalizar(texto: str) -> str:
    if not isinstance(texto, str):
        raise ConsentimientoInvalido("la instantánea tiene que ser texto")

    plano = texto.replace("\r\n", "\n").replace("\r", "\n")
    plano = unicodedata.normalize("NFC", plano)
    return plano.rstrip("\n") + "\n"

def bytes_canonicos(texto: str) -> bytes:
    return canonicalizar(texto).encode("utf-8")

def huella_de(texto: str) -> str:
    return hashlib.sha256(bytes_canonicos(texto)).hexdigest()

@dataclass(frozen=True, slots=True)
class InstantaneaDeVersion:

    codigo: str
    alcance: Alcance
    cuerpo: str
    medio: str = MEDIO_MARKDOWN

    def __post_init__(self) -> None:
        if not isinstance(self.codigo, str) or not self.codigo.strip():
            raise ConsentimientoInvalido("la instantánea necesita el código de su versión")
        object.__setattr__(self, "codigo", self.codigo.strip())
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        if self.medio not in MEDIOS_ADMITIDOS:
            raise ConsentimientoInvalido(
                f"medio «{self.medio}» no admitido; los admitidos son "
                f"{', '.join(MEDIOS_ADMITIDOS)}"
            )
        cuerpo = canonicalizar(self.cuerpo)
        if not cuerpo.strip():

            raise ConsentimientoInvalido(
                "la instantánea no puede estar vacía: sin texto no hay nada que leer"
            )
        if len(cuerpo.encode("utf-8")) > LIMITE_BYTES:
            raise ConsentimientoInvalido(
                f"la instantánea supera {LIMITE_BYTES} bytes; un documento de "
                "consentimiento son páginas, no un volcado"
            )
        object.__setattr__(self, "cuerpo", cuerpo)

    @property
    def huella(self) -> str:
        return huella_de(self.cuerpo)

    @property
    def bytes_canonicos(self) -> bytes:
        return bytes_canonicos(self.cuerpo)

    def coincide_con(self, huella: str) -> bool:
        return isinstance(huella, str) and huella.lower() == self.huella

@dataclass(frozen=True, slots=True)
class PublicacionDeVersion:

    instantanea: InstantaneaDeVersion
    finalidades: frozenset[Finalidad]
    vigente_desde: datetime
    vigente_hasta: datetime | None = None

    def __post_init__(self) -> None:
        finalidades = frozenset(Finalidad(f) for f in self.finalidades)
        faltan = FINALIDADES_OBLIGATORIAS - finalidades
        if faltan:

            raise ConsentimientoInvalido(
                "una versión publicada tiene que cubrir todas las finalidades "
                f"obligatorias; faltan {sorted(f.value for f in faltan)}"
            )
        object.__setattr__(self, "finalidades", finalidades)
        if not isinstance(self.vigente_desde, datetime):
            raise ConsentimientoInvalido("vigente_desde tiene que ser una fecha")
        if self.vigente_hasta is not None and self.vigente_hasta <= self.vigente_desde:
            raise ConsentimientoInvalido(
                "vigente_hasta tiene que ser posterior a vigente_desde"
            )

    @property
    def codigo(self) -> str:
        return self.instantanea.codigo

    @property
    def alcance(self) -> Alcance:
        return self.instantanea.alcance

    @property
    def huella(self) -> str:
        return self.instantanea.huella
