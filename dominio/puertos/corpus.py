from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


MODOS_DE_CAPTURA = ("nativa", "mixta", "ocr", "manual")


_CLAVE_DE_OBRA = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class Procedencia:

    obra: str
    pagina: int
    captura: str = "mixta"
    pagina_hasta: int | None = None

    @property
    def exacta(self) -> bool:
        return self.pagina_hasta is None

    def validar(self) -> list[str]:
        fallos = []
        if not _CLAVE_DE_OBRA.match(self.obra or ""):
            fallos.append(
                f"clave de obra inválida «{self.obra}»: son tres mayúsculas, "
                f"como las del catálogo de fuentes"
            )
        if self.pagina < 1:
            fallos.append(f"página inválida «{self.pagina}»: la numeración empieza en 1")
        if self.pagina_hasta is not None and self.pagina_hasta < self.pagina:

            fallos.append(
                f"rango de páginas invertido: de {self.pagina} a {self.pagina_hasta}"
            )
        if self.captura not in MODOS_DE_CAPTURA:
            fallos.append(f"modo de captura desconocido «{self.captura}»")
        return fallos

@dataclass(frozen=True)
class Fragmento:

    identificador: str
    texto: str
    nivel_apos: str
    registro_duval: str
    procedencia: Procedencia
    concepcion_asociada: str | None = None
    nodo_grafo: str | None = None

    NIVELES_APOS = ("accion", "proceso", "objeto", "esquema")
    REGISTROS_DUVAL = ("algebraico", "grafico", "numerico", "verbal")

    def validar(self) -> list[str]:
        fallos = []
        if not self.texto.strip():
            fallos.append(f"{self.identificador}: texto vacío")
        if self.nivel_apos not in self.NIVELES_APOS:
            fallos.append(f"{self.identificador}: nivel APOS desconocido «{self.nivel_apos}»")
        if self.registro_duval not in self.REGISTROS_DUVAL:
            fallos.append(f"{self.identificador}: registro Duval desconocido «{self.registro_duval}»")
        fallos += [f"{self.identificador}: {f}" for f in self.procedencia.validar()]
        return fallos

@dataclass(frozen=True)
class Recuperacion:

    fragmentos: tuple[Fragmento, ...] = ()
    similitudes: tuple[float, ...] = ()
    sin_fuente: bool = False

    @property
    def utilizable(self) -> bool:
        return bool(self.fragmentos) and not self.sin_fuente

@runtime_checkable
class PuertoCorpus(Protocol):

    def recuperar(self, consulta: str, nodo: str | None = None, k: int = 3) -> Recuperacion:
        ...
