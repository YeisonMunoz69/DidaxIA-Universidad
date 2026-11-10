"""
banco.py — Lee el banco de conceptos de `contenido/conceptos/` · `DD-13`
=========================================================================

`DD-13` decidió que el banco es **contenido versionado y no un subsistema**:
las docentes lo revisan y lo corrigen en Markdown, sin tocar código ni
desplegar. Este módulo es la única pieza que convierte ese Markdown en algo que
una ruta HTTP pueda servir, y por eso vive en `adaptadores/salientes/`: lee de
un almacén de contenido, exactamente como `corpus/cargador.py`.

**No valida ni corrige.** Eso ya lo hace `contenido/conceptos/verificar-conceptos.py`,
que comprueba las aristas, los nodos y la cobertura. Duplicar aquí esas
comprobaciones daría dos veredictos que pueden discrepar — el defecto que este
proyecto lleva registrado tres veces.

⬜ QUÉ SECCIONES VE EL ESTUDIANTE · **es una decisión de contenido y está sin tomar**
--------------------------------------------------------------------------------
`DD-13` describe el banco —«explicación, relaciones y una representación
manipulable»— pero **no dice qué partes de una página llegan al estudiante**, y
las páginas tienen más: procedencia bibliográfica, pendientes de revisión, y una
sección «Cómo se manifiesta» que enumera *lo que el estudiante escribe cuando
tiene esta confusión*.

Mientras eso no se decida, aquí se sirve **lo que explica y no lo que
diagnostica**:

    Qué es · La explicación · Qué hay que entender antes · Qué muestra la
    simulación

Y quedan fuera «Cómo se manifiesta» —es un catálogo de errores ajenos, y
enseñárselo a quien está estudiando se parece demasiado a decirle en qué se
está equivocando—, «Procedencia» y «Qué falta en este archivo», que son
trabajo interno. **El criterio es conservador a propósito: quitar una sección
después es fácil y ponerla ya vista no.** Si Cowork decide otra cosa, se cambia
`SECCIONES_PUBLICAS` y no el resto.



"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

#: Las secciones que llegan al estudiante. Ver la nota de cabecera: es una
#: decisión de contenido sin tomar, y ésta es la lectura conservadora.
SECCIONES_PUBLICAS = (
    "Qué es",
    "La explicación",
    "Qué muestra la simulación",
)

#: De dónde salen los prerrequisitos. Su sección NO va en `SECCIONES_PUBLICAS`:
#: su cuerpo es una tabla Markdown, y servirla como prosa la enseñaría con las
#: barras puestas y además repetida, porque `previos` ya la transporta
#: estructurada. Se lee una vez y se emite de una sola forma.
SECCION_PREVIOS = "Qué hay que entender antes"

#: Filas de la tabla de cabecera que se transportan. El estado se transporta
#: **a propósito**: todas las páginas están en borrador y sin revisión docente,
#: y callarlo dejaría al estudiante leyendo material sin revisar sin saberlo.
_CAMPOS = {
    "Identificador": "id",
    "Nodo del grafo": "nodo",
    "Concepción errónea asociada": "concepcion",
    "Estado": "estado",
}

_TITULO = re.compile(r"^#\s+(\S+)\s+·\s+(.+?)\s*$", re.M)
_FILA = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M)
_SECCION = re.compile(r"^##\s+(.+?)\s*$", re.M)
#: `[`C-M18`](c-m18.md)` — el enlace a otro concepto dentro de una tabla.
_PREVIO = re.compile(r"^\|\s*`(C-[A-Za-z0-9-]+)`\s*\|\s*(.+?)\s*\|\s*$", re.M)

#: El identificador del nodo, dentro de una celda que puede llevar nota.
#:
#: `c-m22.md` escribe «`N14` · *era `N05` hasta el 2026-08-08; `N14` «derivadas
#: de funciones trigonométricas» no existía cuando se escribió este archivo*».
#: Sin esto, `Concepto.nodo` se quedaba la celda ENTERA, y con ella:
#:
#:   · el índice por nodo de `D-28` dejaba `C-M22` fuera de `N14` en silencio,
#:     que es el peor modo de fallar — la única página con la celda anotada;
#:   · y ese texto ya salía por `GET /api/conceptos`, dentro de `como_resumen()`.
#:
#: SE ARREGLA AQUÍ Y NO EN EL ARCHIVO. La nota es contenido de las docentes y
#: `DD-13` dice que el contenido no lo edita el código.
_IDENT_NODO = re.compile(r"N\d+")

# Palabras funcionales que no ayudan a distinguir una explicación de otra.
# El índice se deriva sólo del texto que ya es público para el estudiante: no
# incorpora identificadores, nodos ni la concepción diagnóstica.
_PALABRAS_VACIAS = {
    "ahi", "algo", "ante", "aqui", "cada", "como", "con", "cual", "cuando",
    "del", "desde", "donde", "dos", "el", "ella", "entre", "esa", "ese",
    "esta", "este", "esto", "hay", "las", "los", "mas", "mismo", "muy",
    "para", "pero", "por", "porque", "que", "ser", "sin", "solo", "son",
    "sus", "tambien", "tiene", "una", "uno", "unas", "unos",
}
_CODIGO_INTERNO = re.compile(r"\b(?:C-[A-Z0-9-]+|[NFM]-?\d+)\b", re.I)


def _normalizar_busqueda(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _terminos_de_busqueda(concepto: "Concepto") -> list[str]:
    """Índice humano para el buscador; nunca contiene claves del proyecto."""
    contenido = " ".join(
        [concepto.nombre, *(f"{titulo} {cuerpo}" for titulo, cuerpo in concepto.secciones)]
    )
    contenido = _CODIGO_INTERNO.sub(" ", contenido)
    palabras = re.findall(r"[a-záéíóúüñ]{3,}", contenido, flags=re.I)
    normalizadas = {_normalizar_busqueda(p) for p in palabras}
    return sorted(p for p in normalizadas if p not in _PALABRAS_VACIAS)


@dataclass(frozen=True)
class Concepto:
    """Una página del banco, ya leída."""

    identificador: str
    nombre: str
    nodo: str
    concepcion: str
    estado: str
    secciones: tuple[tuple[str, str], ...]
    previos: tuple[tuple[str, str], ...]

    def como_resumen(self) -> dict:
        """Lo que basta para listar. Sin contenido: `conceptos.js` lo dice —
        «el banco entero, con identificador y nombre. Sin contenido»."""
        return {
            "id": self.identificador,
            "nombre": self.nombre,
            "nodo": self.nodo,
            "estado": self.estado,
            "terminos_busqueda": _terminos_de_busqueda(self),
        }

    def como_ficha(self) -> dict:
        return {
            **self.como_resumen(),
            "concepcion": self.concepcion,
            "secciones": [{"titulo": t, "texto": c} for t, c in self.secciones],
            "previos": [{"id": i, "motivo": m} for i, m in self.previos],
        }


def _limpiar_estado(valor: str) -> str:
    """Quita el emoji y el marcado, deja la frase. «🟡 Borrador · **pendiente
    de revisión docente**» queda en «Borrador · pendiente de revisión docente»."""
    sin_marcado = valor.replace("**", "").replace("`", "")
    return re.sub(r"^[^A-Za-zÁÉÍÓÚÑáéíóúñ]+", "", sin_marcado).strip()


def _sin_notas_al_equipo(cuerpo: str) -> str:
    """Quita las citas `>`, que en este banco son notas para quien implementa.

    «> Esto es lo que `Simulacion.svelte` interpreta» es una instrucción al
    equipo, no una explicación para el estudiante, y llegó a verse en pantalla
    el 2026-08-11. La regla es del formato del banco y no una interpretación:
    todas las páginas usan la cita para lo mismo.
    """
    lineas = [ln for ln in cuerpo.splitlines() if not ln.lstrip().startswith(">")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas))


def _secciones(texto: str) -> dict[str, str]:
    """Cada `##` con su cuerpo, hasta el siguiente `##` o el final."""
    encontradas: dict[str, str] = {}
    marcas = list(_SECCION.finditer(texto))
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[m.end():fin]
        # El separador `---` cierra el cuerpo del documento y no pertenece a
        # ninguna sección; sin quitarlo, la última arrastra el pie de página.
        cuerpo = re.split(r"^---\s*$", cuerpo, maxsplit=1, flags=re.M)[0]
        encontradas[m.group(1).strip()] = _sin_notas_al_equipo(cuerpo).strip()
    return encontradas


def leer(ruta: Path) -> Concepto | None:
    """Una página del banco, o `None` si el archivo no es una."""
    texto = ruta.read_text(encoding="utf-8")

    titulo = _TITULO.search(texto)
    if titulo is None:
        return None

    campos = {}
    for fila in _FILA.finditer(texto):
        clave = _CAMPOS.get(fila.group(1).strip())
        if clave:
            campos[clave] = fila.group(2).strip()

    todas = _secciones(texto)
    previos = [
        (m.group(1), m.group(2))
        for m in _PREVIO.finditer(todas.get(SECCION_PREVIOS, ""))
    ]

    return Concepto(
        identificador=campos.get("id", titulo.group(1)).replace("`", ""),
        nombre=titulo.group(2),
        # Solo el identificador, no la celda: ver `_IDENT_NODO`.
        nodo=(m.group(0) if (m := _IDENT_NODO.search(campos.get("nodo", ""))) else ""),
        concepcion=campos.get("concepcion", "").replace("`", ""),
        estado=_limpiar_estado(campos.get("estado", "")),
        secciones=tuple(
            (t, todas[t]) for t in SECCIONES_PUBLICAS if todas.get(t)
        ),
        previos=tuple(previos),
    )


class BancoDeConceptos:
    """El banco entero, leído del árbol de contenido.

    Se lee **una vez al construirlo**. El banco es contenido versionado: cambia
    cuando alguien edita un archivo y despliega, no durante una conversación.
    Releerlo en cada petición gastaría disco por un cambio que no ocurre.
    """

    def __init__(self, carpeta: Path) -> None:
        self._por_id: dict[str, Concepto] = {}
        #: `D-28` · el índice por nodo del grafo. Se construye AQUÍ y no
        #: recorriendo en cada llamada, por el mismo motivo que la clase
        #: entera se lee una vez: el banco es contenido versionado.
        self._por_nodo: dict[str, list[Concepto]] = {}
        if not carpeta.is_dir():
            return
        for ruta in sorted(carpeta.glob("c-*.md")):
            concepto = leer(ruta)
            if concepto is not None:
                self._por_id[concepto.identificador.upper()] = concepto
                if concepto.nodo:
                    self._por_nodo.setdefault(concepto.nodo.upper(), []).append(concepto)

        # Orden estable por identificador dentro de cada nodo: el panel del
        # estudiante no puede cambiar de orden entre dos turnos que citen el
        # mismo material.
        for paginas in self._por_nodo.values():
            paginas.sort(key=lambda c: c.identificador)

    def __len__(self) -> int:
        return len(self._por_id)

    def listar(self) -> list[Concepto]:
        return sorted(self._por_id.values(), key=lambda c: c.identificador)

    def obtener(self, identificador: str) -> Concepto | None:
        return self._por_id.get((identificador or "").upper())

    def ficha(self, identificador: str) -> dict | None:
        """Ficha pública con los prerrequisitos nombrados para una persona.

        Las claves siguen viajando para abrir la relación, pero nunca se usan
        como rótulo. Resolver el nombre aquí evita que cada pantalla tenga que
        descargar de nuevo el banco o inventar un texto de respaldo técnico.
        """
        concepto = self.obtener(identificador)
        if concepto is None:
            return None
        ficha = concepto.como_ficha()
        for previo in ficha["previos"]:
            relacionado = self.obtener(previo["id"])
            previo["nombre"] = relacionado.nombre if relacionado else "Concepto relacionado"
        return ficha

    def por_nodo(self, nodo: str) -> tuple[Concepto, ...]:
        """Las páginas ancladas en un nodo del grafo · `D-28`.

        Orden estable por identificador: el panel del estudiante no puede
        cambiar de orden entre dos turnos que citen el mismo material.

        ⛔ UN NODO DESCONOCIDO DEVUELVE VACÍO, y no hay respaldo ni nodo por
        defecto. Nueve de los veinticinco nodos tienen página y los otros
        dieciséis no producen nada: es lo que `D-28` §3 decide. Rellenar con
        «algo parecido» sería el servidor eligiendo qué concepto importa, que
        es lo que §6.bis le prohíbe con las mismas palabras que al cliente.
        """
        return tuple(self._por_nodo.get((nodo or "").upper(), ()))
