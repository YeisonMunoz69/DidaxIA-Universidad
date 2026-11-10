"""
corpus.py — Puerto de recuperación de contexto (S7 · S8)
========================================================

`ADR-002` fijó la estrategia —híbrido jerárquico grafo→vectorial con k=3— y
`ADR-006` U1 el umbral de similitud coseno ≥0,70 con modo *sin fuente*.
`ADR-010` dejó el **almacén** condicionado a una medición pendiente.
`DD-15` §Corpus exige que cada fragmento conserve su procedencia.

Que el almacén esté sin decidir y la construcción pueda seguir es precisamente
la propiedad que `ADR-001` §6.2 introdujo. El dominio depende de este puerto,
no de un producto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: Cómo se obtuvo el texto de un fragmento. Existe porque ninguna de las obras
#: conserva sus fórmulas al extraerlas —ni siquiera el PDF generado con LaTeX—,
#: de modo que la matemática se transcribe a mano y eso hay que poder saberlo
#: después sin volver a abrir el libro. Ver `corpus/ESTRATEGIA-DE-EXTRACCION.md`.
MODOS_DE_CAPTURA = ("nativa", "mixta", "ocr", "manual")

#: Forma de la clave de obra: tres letras mayúsculas, como `PUR` o `SWO`.
_CLAVE_DE_OBRA = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class Procedencia:
    """De qué obra y qué página sale un fragmento.

    **No es formalismo bibliográfico.** `DD-15` §Corpus autoriza el material de
    las docentes solo para las pruebas del objetivo 4, y de ahí su consecuencia:
    *«un corpus sin procedencia no se puede depurar, solo borrar entero»*. Si
    mañana hay que retirar lo que salió de una obra concreta, la diferencia
    entre un rato y rehacerlo todo está en si se anotó de dónde salió cada cosa.

    Es además lo que `DD-02` necesita para verificar la matemática al ingerir:
    sin saber de dónde viene un fragmento no hay contra qué comprobarlo.

    - `obra` — la **clave** de `corpus/FUENTES.md`, no el título. El catálogo
      vive en un solo sitio y aquí se referencia, que es la regla de
      `COMO-TRABAJAMOS.md` §1. Que la clave exista se comprueba a nivel de
      contenido: el dominio no lee archivos.
    - `pagina` — la de la **edición impresa**, no la hoja del archivo. En `SWO`
      las dos difieren en 17 porque el escaneo arranca antes.
    - `pagina_hasta` — **cuando la página no se conoce con exactitud**, el final
      del rango en el que está el fragmento. Ver abajo y `DD-21`.
    - `captura` — cómo se obtuvo. Ver `MODOS_DE_CAPTURA`.

    Exacta o aproximada, y por qué se distingue
    -------------------------------------------
    `DD-21`, del 2026-08-06: **las obras no imprimen el número en todas sus
    páginas**, de modo que exigir la exacta por fragmento dejaría fuera buena
    parte del material. Se admite un rango, y **el rango se declara como tal** en
    lugar de guardar un número cualquiera de dentro.

    La distinción no es formalismo. Al citar un pasaje en el documento de grado,
    una página exacta se escribe y una aproximada **no se puede escribir como si
    lo fuera**. Guardar «201» sin poder saber después si es exacto o estimado es
    justo el dato que la procedencia existe para no perder.
    """

    obra: str
    pagina: int
    captura: str = "mixta"
    pagina_hasta: int | None = None

    @property
    def exacta(self) -> bool:
        """Si la página se conoce con precisión de una sola página."""
        return self.pagina_hasta is None

    def validar(self) -> list[str]:
        """Errores de la procedencia. Lista vacía significa que es admisible."""
        fallos = []
        if not _CLAVE_DE_OBRA.match(self.obra or ""):
            fallos.append(
                f"clave de obra inválida «{self.obra}»: son tres mayúsculas, "
                f"como las de corpus/FUENTES.md"
            )
        if self.pagina < 1:
            fallos.append(f"página inválida «{self.pagina}»: la numeración empieza en 1")
        if self.pagina_hasta is not None and self.pagina_hasta < self.pagina:
            # Un rango invertido casi siempre es un descuido al anotar, y sin
            # esta comprobación produce un fragmento que dice estar entre la 204
            # y la 198 sin que nada proteste.
            fallos.append(
                f"rango de páginas invertido: de {self.pagina} a {self.pagina_hasta}"
            )
        if self.captura not in MODOS_DE_CAPTURA:
            fallos.append(f"modo de captura desconocido «{self.captura}»")
        return fallos


@dataclass(frozen=True)
class Fragmento:
    """Unidad del corpus, con los metadatos que la revisión exige anotar.

    Los tres campos de metadato no son opcionales por capricho:

    - `nivel_apos` — `RF-COR-01`. APOS es el marco predominante del Eje C, y
      el único hallazgo del corpus con certeza CERQual Moderada.
    - `registro_duval` — `RF-COR-01`. Duval distingue tratamiento de
      conversión, y el reordenamiento de `RF-GPE-13` usa el cambio de registro
      respecto al turno anterior.
    - `concepcion_asociada` — `RF-COR-02`. Es la arista que en el experimento
      E01 produjo 0,800 de recall diagnóstico frente a 0,300 del vectorial:
      cuando el estudiante enuncia una concepción errónea, la similitud
      semántica lleva al concepto equivocado.

    Y uno que no viene de la revisión sino de `DD-15`:

    - `procedencia` — **obligatoria**. Un fragmento sin ella no se puede
      retirar selectivamente, y retirar es lo que la autorización del material
      contempla. Por eso no admite valor por defecto: omitirla tiene que ser un
      error en el momento de construir el fragmento, no un hueco que aparezca
      el día que haya que depurar.
    """

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
        """Errores del fragmento. Lista vacía significa que es admisible."""
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
    """Lo que devuelve una consulta al corpus."""

    fragmentos: tuple[Fragmento, ...] = ()
    similitudes: tuple[float, ...] = ()
    sin_fuente: bool = False

    @property
    def utilizable(self) -> bool:
        """`ADR-006` U2: sin fragmento sobre umbral se opera en modo sin fuente."""
        return bool(self.fragmentos) and not self.sin_fuente


@runtime_checkable
class PuertoCorpus(Protocol):
    """Contrato de recuperación. El almacén concreto es asunto del adaptador."""

    def recuperar(self, consulta: str, nodo: str | None = None, k: int = 3) -> Recuperacion:
        """Recupera fragmentos filtrados por nodo, con umbral aplicado."""
        ...
