from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


_CLAVE_DE_OBRA = re.compile(r"^[A-Z]{3}$")


_IDENTIFICADOR_DE_FRAGMENTO = re.compile(r"^F-\d{3}$")


_IDENTIFICADOR_DE_PARTE = re.compile(r"^[A-Z]{3}:[a-z0-9][a-z0-9-]{0,63}$")


_NOMBRE_SIMPLE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}\.(md|pdf)$")


class Canal(StrEnum):

    FRAGMENTO = "fragmento"
    MARKDOWN_CONTINUO = "markdown_continuo"
    PDF_DIVIDIDO = "pdf_dividido"
    PDF_COMPLETO = "pdf_completo"

class Permiso(StrEnum):

    PERMITIDO = "permitido"
    PENDIENTE = "pendiente"
    BLOQUEADO = "bloqueado"
    RETIRADO = "retirado"
    FUERA_DEL_CORPUS = "fuera_del_corpus"

    @property
    def habilita(self) -> bool:
        return self is Permiso.PERMITIDO

class MotivoIndisponible(StrEnum):

    FRAGMENTO_INEXISTENTE = "fragmento_inexistente"

    RECURSO_NO_CATALOGADO = "recurso_no_catalogado"

    OBRA_NO_AUTORIZADA = "obra_no_autorizada"

    ARCHIVO_AUSENTE = "archivo_ausente"

    PAGINA_SIN_MAPEO = "pagina_sin_mapeo"

    RECURSO_NO_SERVIBLE = "recurso_no_servible"

    RECURSO_RETIRADO = "recurso_retirado"

class Indisponible(Exception):

    def __init__(self, motivo: MotivoIndisponible, detalle: str = "") -> None:
        super().__init__(detalle or motivo.value)
        self.motivo = motivo
        self.detalle = detalle

@dataclass(frozen=True)
class Disponibilidad:

    canal: Canal
    permiso: Permiso
    catalogado: bool = False
    archivo_presente: bool = False

    @property
    def servible(self) -> bool:
        return self.permiso.habilita and self.catalogado and self.archivo_presente

    def motivo(self) -> MotivoIndisponible | None:
        if self.permiso is Permiso.RETIRADO:
            return MotivoIndisponible.RECURSO_RETIRADO
        if not self.permiso.habilita:
            return MotivoIndisponible.OBRA_NO_AUTORIZADA
        if not self.catalogado:
            return MotivoIndisponible.RECURSO_NO_CATALOGADO
        if not self.archivo_presente:
            return MotivoIndisponible.ARCHIVO_AUSENTE
        return None

@dataclass(frozen=True)
class Obra:

    clave: str
    titulo: str

    autoria: str = ""

    paginas_del_archivo: int | None = None

    referencia_externa: str = ""
    referencia_verificada: bool = False

    disponibilidad: dict[Canal, Disponibilidad] = field(default_factory=dict)

    def validar(self) -> list[str]:
        fallos = []
        if not _CLAVE_DE_OBRA.match(self.clave or ""):
            fallos.append(f"clave de obra inválida «{self.clave}»: son tres mayúsculas")
        if not self.titulo.strip():
            fallos.append(f"{self.clave}: sin título legible")
        return fallos

    def permiso_de(self, canal: Canal) -> Permiso:
        vista = self.disponibilidad.get(canal)
        return vista.permiso if vista else Permiso.BLOQUEADO

@dataclass(frozen=True)
class Parte:

    identificador: str
    obra: str
    titulo: str
    pagina_impresa_inicial: int
    pagina_impresa_final: int

    archivo_markdown: str = ""

    archivo_pdf: str = ""

    def validar(self) -> list[str]:
        fallos = []
        if not _IDENTIFICADOR_DE_PARTE.match(self.identificador or ""):
            fallos.append(f"identificador de parte inválido «{self.identificador}»")
        if not _CLAVE_DE_OBRA.match(self.obra or ""):
            fallos.append(f"{self.identificador}: clave de obra inválida «{self.obra}»")
        elif not self.identificador.startswith(f"{self.obra}:"):
            fallos.append(
                f"{self.identificador}: el identificador no empieza por su obra «{self.obra}»"
            )
        if self.pagina_impresa_inicial < 1:
            fallos.append(f"{self.identificador}: página inicial inválida")
        if self.pagina_impresa_final < self.pagina_impresa_inicial:
            fallos.append(
                f"{self.identificador}: rango invertido "
                f"({self.pagina_impresa_inicial}–{self.pagina_impresa_final})"
            )
        for campo, valor in (("markdown", self.archivo_markdown), ("pdf", self.archivo_pdf)):
            if valor and not _NOMBRE_SIMPLE.match(valor):
                fallos.append(
                    f"{self.identificador}: nombre de archivo {campo} no admisible «{valor}»"
                )
        return fallos

    def contiene(self, pagina_impresa: int) -> bool:
        return self.pagina_impresa_inicial <= pagina_impresa <= self.pagina_impresa_final

@dataclass(frozen=True)
class Localizacion:

    obra: str
    parte: str
    pagina_impresa: int
    pagina_interna_en_parte: int

    pagina_interna_en_obra: int | None = None

    pagina_impresa_hasta: int | None = None

    @property
    def exacta(self) -> bool:
        return self.pagina_impresa_hasta is None

@runtime_checkable
class PuertoBiblioteca(Protocol):

    def obra(self, clave: str) -> Obra:
        ...

    def obras(self) -> tuple[Obra, ...]:
        ...

    def parte(self, identificador: str) -> Parte:
        ...

    def partes_de(self, clave: str) -> tuple[Parte, ...]:
        ...

    def localizar(
        self, clave: str, pagina_impresa: int, pagina_hasta: int | None = None
    ) -> Localizacion:

        ...

    def disponibilidad(self, clave: str, canal: Canal) -> Disponibilidad:
        ...

def clave_de_obra_valida(clave: str) -> bool:
    return bool(_CLAVE_DE_OBRA.match(clave or ""))

def identificador_de_fragmento_valido(identificador: str) -> bool:
    return bool(_IDENTIFICADOR_DE_FRAGMENTO.match(identificador or ""))

def identificador_de_parte_valido(identificador: str) -> bool:
    return bool(_IDENTIFICADOR_DE_PARTE.match(identificador or ""))

def nombre_de_archivo_admisible(nombre: str) -> bool:
    return bool(_NOMBRE_SIMPLE.match(nombre or ""))
