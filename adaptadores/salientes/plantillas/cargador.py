"""
cargador.py — Lee el andamiaje socrático desde `contenido/plantillas/` (`PM-B06`)
=========================================================================================

Cierra el mismo tipo de hueco que `adaptadores/salientes/corpus/cargador.py`
cerró en el incremento 1, y por el mismo motivo: el contenido existía —los
dieciséis archivos de `PM-C14`, del 2026-08-10— y **nada los leía**. El filtro 7
mandaba tres líneas de andamio genérico al generador mientras la pedagogía del
trabajo de grado esperaba en disco.

Por qué es un adaptador y no dominio
------------------------------------------
`ADR-001` §6.2: el dominio no toca el sistema de archivos. La consecuencia se
ve en cómo se reparte el conocimiento, igual que en el cargador del corpus:

| Quién | Qué sabe | Por qué ahí |
|---|---|---|
| `dominio/puertos/plantillas.py` | Que hay cinco clases de andamiaje y que las secuencias son por concepción | Es vocabulario pedagógico |
| `dominio/pedagogia/politica.py` | **Cuál** toca en cada situación | Es una regla pedagógica, y se lee como tabla |
| Este adaptador | Que `SCAFFOLDING_KQ` vive en `p-scaffolding-kq1-kq5.md` | Requiere abrir un directorio |

Los nombres de archivo **solo aparecen aquí**. `_ARCHIVO_DE_CLAVE` es esa
traducción, explícita y en un sitio: derivarla del nombre de la clave habría
atado el vocabulario del dominio a cómo Fabián decidió llamar sus archivos, y
renombrar uno habría roto el dominio en silencio.

🔴 La frontera del repertorio · `D-5`, fase 4
------------------------------------------------
Hasta la fase 4 la regla era *«toda cita `«…»` que esté en una fila de tabla o
en una cita en bloque»*. Esa regla ya había atrapado un defecto —los
anti-ejemplos en prosa corrida— y **seguía dejando pasar dos, medidos sobre el
contenido real**:

| Qué entraba | De dónde | Por qué es grave |
|---|---|---|
| «revisa el ejercicio» | `p-scaffolding-kq1-kq5.md`, celda *«Qué se busca»* de la fila `KQ1` | Es el anti-ejemplo de esa fila: el prompt recibía como modelo lo que la plantilla existe para evitar |
| «Cómo se manifiesta» | ídem, cita en bloque explicativa | Es el nombre de una sección del banco de conceptos, no una pregunta |
| «¿qué estrategia vas a usar y por qué?» y «¿cómo sabrías que tu respuesta es razonable?» | `p-autorregulacion.md`, fila **Criterio de aceptación** | Son los ejemplos del criterio, no dos de las catorce variantes: `P-AUTORREGULACION` producía **16** donde declara 14 |

Y **perdía** repertorio en silencio: una cita partida en dos líneas dentro de
una misma cita en bloque no casaba con ninguna de las dos mitades, así que
`s-m21.md` producía cuatro pasos de los cinco que tiene escritos.

La frontera nueva tiene **dos capas, y hacen falta las dos**:

1. **La región declarada.** El repertorio productivo va entre
   `<!-- repertorio: inicio -->` y `<!-- repertorio: fin -->`. Es un comentario
   de Markdown: no se ve al leer el documento renderizado, y una docente lo
   entiende sin saber programar. Lo que queda fuera —la tabla de metadatos, el
   criterio de aceptación, las explicaciones— **no puede entrar al prompt por
   descuido**.
2. **La marca de repertorio.** Dentro de la región, sólo cuenta la cita
   **enfatizada** —`*«…»*`, `**«…»**`, `_«…»_`—, que es la convención que
   `PM-C14` ya siguió al escribir las preguntas. Es lo que separa la pregunta
   del anti-ejemplo **dentro de la misma fila**, que la región sola no puede
   hacer.

Y las citas en bloque se leen **por bloque**, no por línea: un `>` seguido de
otro `>` es una sola unidad, así que una cita partida por el ancho del
documento se recupera entera.

**Una delimitación inválida no degrada en silencio.** Un archivo sin marcadores,
o con uno abierto sin cerrar, produce **cero** repertorio y un problema
declarado en `problemas`, que `composicion.py` publica en `/api/salud`. La
alternativa —caer a la regla vieja— sería exactamente el modo de fallo que esto
viene a cerrar: contenido mal delimitado interpretado como repertorio válido.

Lo que este módulo NO hace
--------------------------------
**No valida la pedagogía.** Que una secuencia lleve al estudiante donde
pretende es una afirmación empírica y su sitio es `PM-V05`, como el propio
LEEME del contenido declara. Aquí solo se lee.

**No falla por contenido ausente.** Un archivo que no está devuelve `None` y
nunca una excepción: `contenido/` cambia bajo los pies del código —hay once
secuencias de veinticuatro concepciones posibles— y un turno no puede caerse
porque una concepción todavía no tenga la suya. Es la misma propiedad que
`_CorpusVacio` le da a la recuperación en `composicion.py`.


"""

from __future__ import annotations

import re
from pathlib import Path

from adaptadores.salientes.plantillas.items import items_desde_texto
from dominio.puertos.plantillas import (
    AUTOCONCEPTO,
    AUTORREGULACION,
    SCAFFOLDING_KQ,
    SOCRATICA_APOS,
    TWO_TIER,
    ItemDosNiveles,
    Plantilla,
)

#: La única traducción clave→archivo del sistema. Ver la cabecera del módulo
#: sobre por qué es explícita y no derivada del nombre.
_ARCHIVO_DE_CLAVE = {
    SOCRATICA_APOS: "p-socratica-apos.md",
    SCAFFOLDING_KQ: "p-scaffolding-kq1-kq5.md",
    TWO_TIER: "p-two-tier.md",
    AUTOCONCEPTO: "p-retroalimentacion-autoconcepto.md",
    AUTORREGULACION: "p-autorregulacion.md",
}

#: Los delimitadores de la región productiva. Comentario de Markdown a
#: propósito: invisible al renderizar, legible al editar.
MARCA_INICIO = "<!-- repertorio: inicio -->"
MARCA_FIN = "<!-- repertorio: fin -->"

#: La cita **enfatizada**, que es la marca de repertorio de `PM-C14`. Un
#: anti-ejemplo citado dentro de la misma celda va sin énfasis, y ésa es la
#: diferencia que la región sola no puede ver.
_PREGUNTA = re.compile(r"(?:\*\*|\*|__|_)«([^»]+)»(?:\*\*|\*|__|_)")

#: De dónde se admite, ya dentro de la región: fila de tabla o cita en bloque.
#: La prosa explicativa sigue fuera aunque esté delimitada — dos capas que se
#: solapan cuestan nada y tapan dos descuidos distintos.
_FILA = "|"
_CITA = ">"

#: El título es el `# …` de la primera línea, como en cualquier documento del
#: proyecto. Si no lo hay se usa la clave: un título ausente no justifica
#: descartar las preguntas, que son lo que de verdad se busca.
_TITULO = re.compile(r"^#\s+(.+)$", re.M)

#: `s-m21.md` → `M21`. El catálogo del contenido es `M01`–`M24`, en mayúscula;
#: el archivo va en minúscula, que es la costumbre del resto del árbol.
_SECUENCIA = re.compile(r"^s-(m\d{2})\.md$", re.I)


class CargadorDePlantillas:
    """Sirve `contenido/plantillas/` como `PuertoPlantillas`.

    Lee el directorio **una vez al construirse**, igual que
    `BancoDeConceptos` con `DD-13`: es contenido versionado, no cambia
    durante la vida del proceso, y releerlo por turno gastaría E/S en la ruta
    caliente para obtener lo mismo.
    """

    def __init__(self, directorio: Path) -> None:
        self._por_concepcion: dict[str, Plantilla] = {}
        self._por_clave: dict[str, Plantilla] = {}
        #: Qué archivos no se pudieron leer como repertorio, y por qué. Se
        #: publica: un contenido mal delimitado tiene que notarse antes de que
        #: las respuestas empeoren sin motivo aparente.
        self._problemas: list[str] = []
        #: `PM-B08`, enganchado el 2026-08-13. Por nodo del grafo y no por
        #: clave: un ítem es de un nodo, y `RC-PED-06` pide tres —`N08`,
        #: `N14`, `N05`—, los tres escritos con sus razones desde `PM-C15`
        #: (2026-08-14).
        self._items_por_nodo: dict[str, ItemDosNiveles] = {}
        self._cargar(directorio)

    def _cargar(self, directorio: Path) -> None:
        if not directorio.is_dir():
            # Sin directorio no hay andamiaje y el sistema sigue con el suyo.
            # No es un error del cargador: es el estado de un despliegue que
            # todavía no monta `contenido/`.
            return
        for archivo in sorted(directorio.glob("*.md")):
            texto = _leer(archivo)
            if texto is None:
                self._problemas.append(f"{archivo.name}: no se pudo leer")
                continue
            secuencia = _SECUENCIA.match(archivo.name)
            if secuencia is not None:
                concepcion = secuencia.group(1).upper()
                self._por_concepcion[concepcion] = self._plantilla(
                    concepcion, texto, archivo.name
                )
                continue
            for clave, nombre in _ARCHIVO_DE_CLAVE.items():
                if archivo.name == nombre:
                    self._por_clave[clave] = self._plantilla(clave, texto, archivo.name)
                    if clave == TWO_TIER:
                        # El mismo archivo sirve dos lecturas distintas: su
                        # repertorio de preguntas (arriba) y sus ítems
                        # estructurados. Ver `items.py` sobre por qué los
                        # segundos viven en otro módulo, y por qué la
                        # delimitación del repertorio no los toca: `items.py`
                        # lee la estructura del documento, no las citas.
                        #
                        # Con nodo repetido gana el ÚLTIMO, y da igual cuál:
                        # dos secciones para el mismo nodo son un error de
                        # contenido y elegir bien entre ellas sería fingir que
                        # no lo es. Lo que no puede pasar es reventar aquí.
                        for item in items_desde_texto(texto):
                            self._items_por_nodo[item.nodo] = item
                    break

    def _plantilla(self, clave: str, texto: str, archivo: str) -> Plantilla:
        titulo = _TITULO.search(texto)
        preguntas, problema = repertorio(texto)
        if problema:
            self._problemas.append(f"{archivo}: {problema}")
        return Plantilla(
            clave=clave,
            titulo=titulo.group(1).strip() if titulo else clave,
            preguntas=preguntas,
            diagnostico=problema,
        )

    def secuencia_de(self, concepcion: str) -> Plantilla | None:
        return self._por_concepcion.get(concepcion.strip().upper())

    def plantilla(self, clave: str) -> Plantilla | None:
        return self._por_clave.get(clave)

    def item_de(self, nodo: str) -> ItemDosNiveles | None:
        return self._items_por_nodo.get(nodo.strip().upper())

    def nodo_del_ejercicio(self, expresion: str) -> str | None:
        """Paquete B · el nodo cuyo ítem plantea este ejercicio, o `None`.

        Se compara con `normalizar_expresion()` —la misma que la unidad de
        problema usa para decidir si dos turnos hablan del mismo ejercicio—,
        así que `cos(x)^3` y `COS(X)^3 ` son el mismo. Reutilizarla, y no
        escribir aquí una segunda comparación, es lo que impide que el sistema
        tenga dos ideas de cuándo dos expresiones son la misma.
        """
        from dominio.pedagogia.problema import (  # noqa: PLC0415
            normalizar_expresion,
        )

        clave = normalizar_expresion(expresion)
        if not clave:
            return None
        for nodo, item in self._items_por_nodo.items():
            if item.derivar and normalizar_expresion(item.derivar) == clave:
                return nodo
        return None

    @property
    def cuantas(self) -> tuple[int, int]:
        """Cuántas secuencias y cuántas plantillas se leyeron.

        Para que `composicion.py` pueda declarar en `/api/salud` qué encontró,
        en vez de que un directorio vacío se note por que las respuestas
        empeoran sin motivo aparente.
        """
        return len(self._por_concepcion), len(self._por_clave)

    @property
    def problemas(self) -> tuple[str, ...]:
        """Los archivos cuya delimitación no se pudo leer, con su motivo.

        Vacío es lo normal. Que no lo esté significa que **ese** archivo entra
        al sistema sin repertorio, no que el sistema esté roto: los demás
        siguen sirviendo el suyo.
        """
        return tuple(self._problemas)


def _leer(archivo: Path) -> str | None:
    """El texto, o `None` si no se puede leer.

    Un archivo ilegible no tumba la carga de los otros quince — la misma
    disciplina que `cargar()` del corpus, que separa fragmentos de fallos en
    vez de abortar entero.
    """
    try:
        return archivo.read_text(encoding="utf-8")
    except OSError:
        return None


def _regiones(lineas: list[str]) -> tuple[list[list[str]], str]:
    """Los bloques delimitados, o el motivo por el que no se pueden leer.

    Devuelve `(regiones, problema)`. Con `problema` no vacío las regiones van
    vacías **a propósito**: caer a leer el archivo entero sería tratar un
    contenido mal delimitado como repertorio válido, que es lo que `D-5` cierra.
    """
    regiones: list[list[str]] = []
    dentro = False
    actual: list[str] = []
    for numero, linea in enumerate(lineas, start=1):
        plano = linea.strip()
        if plano == MARCA_INICIO:
            if dentro:
                return [], f"«repertorio: inicio» anidado en la línea {numero}"
            dentro = True
            actual = []
            continue
        if plano == MARCA_FIN:
            if not dentro:
                return [], f"«repertorio: fin» sin apertura en la línea {numero}"
            regiones.append(actual)
            dentro = False
            continue
        if dentro:
            actual.append(linea)
    if dentro:
        return [], "«repertorio: inicio» sin su «repertorio: fin»"
    if not regiones:
        return [], "sin delimitación de repertorio"
    return regiones, ""


def _unidades(region: list[str]) -> list[str]:
    """Las unidades de las que se extrae: filas de tabla y citas en bloque.

    Una cita en bloque es **el grupo entero de líneas `>` consecutivas**, unidas
    por un espacio. Leerlas por línea suelta partía en dos las citas que no
    caben en el ancho del documento, y entonces ninguna de las dos mitades
    casaba: `s-m21.md` perdía así su `KQ5`.
    """
    unidades: list[str] = []
    cita: list[str] = []
    for linea in region:
        pelada = linea.lstrip()
        if pelada.startswith(_CITA):
            cita.append(pelada.lstrip(">").strip())
            continue
        if cita:
            unidades.append(" ".join(cita))
            cita = []
        if pelada.startswith(_FILA):
            unidades.append(pelada)
    if cita:
        unidades.append(" ".join(cita))
    return unidades


def repertorio(texto: str) -> tuple[tuple[str, ...], str]:
    """El repertorio productivo del documento, y el problema si no lo tiene.

    Es la frontera de `D-5` en una función: región declarada, unidad de tabla o
    de cita, y cita **enfatizada** dentro de ella. Ver la cabecera del módulo
    sobre por qué hacen falta las tres condiciones y qué entraba sin cada una.
    """
    regiones, problema = _regiones(texto.splitlines())
    if problema:
        return (), problema

    salida: list[str] = []
    for region in regiones:
        for unidad in _unidades(region):
            for cruda in _PREGUNTA.findall(unidad):
                # Una cita puede traer saltos de tabla o espacios de sobra: se
                # normaliza para que el prompt no herede el formato del Markdown.
                limpia = " ".join(cruda.split())
                if limpia:
                    salida.append(limpia)
    if not salida:
        return (), "el repertorio delimitado no contiene ninguna cita enfatizada"
    return tuple(salida), ""
