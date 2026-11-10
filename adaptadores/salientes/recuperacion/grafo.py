"""
grafo.py — El grafo pedagógico, en memoria (S8 · S6)
====================================================

`ADR-010` decidió **grafo en memoria, con la definición versionada como archivo
de texto y cargada al arrancar**, y declaró por qué no una base de datos de
grafos: no hay ningún requisito de escala, de consulta arbitraria ni de
concurrencia que lo justifique, e introducirla sería *«elegir por reputación»*.

`06-Guia-de-Reutilizacion.md` §3 dictamina `kb/graph_store.py` como ♻️ —se
reutiliza tal cual— nombrando dos métodos: `neighbors()` y
`get_misconceptions_for()`. **La arista `misconception_asociada` es la que
produce el 0,800 de recall diagnóstico de E01 frente al 0,300 del vectorial**,
que es evidencia propia sobre un vacío del corpus y el motivo de `ADR-006`.

Divergencia declarada respecto al ♻️
------------------------------------
La iteración 0 apoya esas dos operaciones en **networkx**. Aquí no, y conviene
que el motivo quede escrito en lugar de descubrirse leyendo los imports:

- El grafo tiene **25 nodos y 39 aristas** —eran 17 y 26 cuando esto se escribió,
  y `PM-C09` lo amplió el 2026-08-08—. Una lista de adyacencia en un diccionario
  resuelve vecindad y filtrado por tipo sin dependencia externa, y el argumento no
  cambia con el tamaño: lo que pediría una biblioteca de grafos es otra operación,
  no más nodos.
- La única operación del original que sí pediría una biblioteca de grafos es
  `shortest_path`, y **no se traslada**: la ruta pedagógica es asunto de `S6`,
  que el plan de construcción sitúa en el incremento 4. Traerla ahora sería
  código sin requisito al que trazarlo, que es lo que la guía §5 prohíbe.

**Lo que se conserva tal cual es la semántica**, que es lo que el ♻️ protege:
los mismos nombres de arista, el mismo criterio de sucesor y el mismo
comportamiento ante un nodo inexistente —lista vacía, no excepción—, porque el
respaldo automático de `ADR-002` depende de que no encontrar nodo sea un caso
normal y no un error.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: Tipos de arista que la definición usa hoy. Se comprueba al cargar: una arista
#: de tipo desconocido es casi siempre una errata, y en un archivo escrito a mano
#: pasa inadvertida hasta que una consulta deja de devolver lo que debía.
TIPOS_DE_ARISTA = (
    "prerrequisito_de",
    "misconception_asociada",
    "se_confunde_con",
    "caso_especial_de",
    "representacion_alternativa_de",
)

#: La arista que `ADR-006` convierte en ruta diagnóstica.
MISCONCEPCION = "misconception_asociada"

#: Categoría con la que la definición marca a `M1`–`M5`. **No son temas.** Viven
#: en el grafo porque son el destino de la arista de `ADR-006`, no porque se les
#: pueda recuperar material: `DD-22` exige `nodo_grafo` en cada fragmento y
#: ninguno de los 148 indexados declara una `M*`. La distinción se usa en
#: `jerarquico.py` para no tomarlas como nodo de entrada.
CATEGORIA_MISCONCEPCION = "Misconception"


@dataclass(frozen=True)
class Nodo:
    """Concepto del grafo, con lo que la definición anota de él."""

    identificador: str
    etiqueta: str
    categoria: str = ""
    apos: str = ""
    descripcion: str = ""
    indicador_observable: str = ""
    #: Otros nombres del mismo concepto **para la cobertura del corpus**. Cada
    #: uno sale de un título que existe en una obra, no de memoria — es la regla
    #: de `NODOS-CANDIDATOS.md` §1.bis. Lo lee `inventario-de-cobertura.py`.
    #:
    #: ⚠️ **Desde `PM-C17` esto ya NO enruta preguntas.** Entre el 2026-08-08 y
    #: el 2026-08-14 este mismo campo servía a los dos instrumentos, y `PM-C16`
    #: midió que se quieren lo contrario: la cobertura premia la forma que casa
    #: **muchos títulos** y la identificación necesita la que casa **pocas
    #: preguntas**. Ver `formas_de_consulta`.
    sinonimos: tuple[str, ...] = ()
    #: Las formas con las que un estudiante puede nombrar este nodo **en una
    #: pregunta**. Lo lee `jerarquico.py`, junto con la etiqueta. `D-25` opción
    #: `A`, `PM-C17`.
    #:
    #: **`None` significa que la definición no lo dice**, y no es lo mismo que
    #: la lista vacía: `validar()` lo denuncia cuando el nodo sí declara
    #: `sinonimos`, porque un reparto a medias se lee como «este nodo no se
    #: nombra de ninguna otra manera» y eso no falla, solo recupera peor.
    formas_de_consulta: tuple[str, ...] | None = None


class GrafoEnMemoria:
    """Grafo pedagógico cargado de su archivo de definición.

    Se construye una vez al arrancar. No se recarga en caliente: la definición
    es **contenido versionado**, de modo que un cambio pasa por el repositorio y
    por su revisión, no por el sistema en marcha.
    """

    def __init__(self, definicion: dict) -> None:
        self._nodos: dict[str, Nodo] = {}
        self._salientes: dict[str, list[tuple[str, str]]] = {}

        for n in definicion.get("nodes", []):
            self._nodos[n["id"]] = Nodo(
                identificador=n["id"],
                etiqueta=n.get("label", ""),
                categoria=n.get("categoria", ""),
                apos=n.get("apos", ""),
                descripcion=n.get("descripcion", ""),
                indicador_observable=n.get("indicador_observable", ""),
                sinonimos=tuple(n.get("sinonimos", ())),
                formas_de_consulta=(
                    tuple(n["formas_de_consulta"])
                    if "formas_de_consulta" in n
                    else None
                ),
            )

        for e in definicion.get("edges", []):
            self._salientes.setdefault(e["source"], []).append((e["target"], e["type"]))

    # -- construcción -----------------------------------------------------

    @classmethod
    def desde_archivo(cls, ruta: Path) -> GrafoEnMemoria:
        """Carga la definición versionada."""
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def validar(self) -> list[str]:
        """Errores de la definición. Lista vacía significa que es admisible.

        Comprueba lo que un archivo escrito a mano se equivoca de verdad: una
        arista que apunta a un nodo que no existe —casi siempre una errata en el
        identificador—, un tipo de arista inventado y **un nodo que declara
        sinónimos sin decir cuáles enrutan**. Los tres fallan en silencio si
        nadie los mira: la consulta simplemente devuelve menos.
        """
        fallos = []
        # `PM-C17`. El caso que esto atrapa es el de dentro de un mes: alguien
        # añade un sinónimo nuevo a un nodo y no toca `formas_de_consulta`
        # porque no sabe que existe. Con la lista declarada, ese sinónimo
        # simplemente no enruta —y nadie se entera, porque el respaldo plano de
        # `ADR-002` responde igual, solo que peor.
        for identificador in self.conceptos():
            nodo = self._nodos[identificador]
            if nodo.sinonimos and nodo.formas_de_consulta is None:
                fallos.append(
                    f"{identificador}: declara «sinonimos» y no «formas_de_consulta»"
                    " — el reparto de D-25 quedó a medias"
                )
        for origen, destinos in self._salientes.items():
            if origen not in self._nodos:
                fallos.append(f"arista desde un nodo inexistente «{origen}»")
            for destino, tipo in destinos:
                if tipo not in TIPOS_DE_ARISTA:
                    fallos.append(f"{origen}→{destino}: tipo de arista desconocido «{tipo}»")
                # Las concepciones erróneas son `M01`–`M24` y viven en el
                # catálogo de la revisión, no en el grafo: no se exige que
                # existan como nodo.
                if tipo != MISCONCEPCION and destino not in self._nodos:
                    fallos.append(f"{origen}→{destino}: destino inexistente")
        return fallos

    # -- consulta ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self._nodos)

    @property
    def total_aristas(self) -> int:
        return sum(len(v) for v in self._salientes.values())

    def identificadores(self) -> tuple[str, ...]:
        """Los identificadores de todos los nodos, en orden estable.

        Existe para que quien necesite recorrer el grafo no tenga que alcanzar
        su diccionario interno. El orden es el del identificador y no el del
        archivo: así una reordenación de la definición no cambia el resultado
        de nada que dependa de recorrerlo.
        """
        return tuple(sorted(self._nodos))

    def conceptos(self) -> tuple[str, ...]:
        """Los nodos que **son temas**: todos menos las concepciones erróneas.

        Existe porque identificar el nodo de entrada y recorrer el grafo son dos
        cosas distintas. `M1`–`M5` son destinos legítimos de una arista y no
        deben desaparecer de `identificadores()`; lo que no pueden ser es
        *entrada* de la recuperación, porque no tienen material que recuperar.
        Medido el 2026-08-09 sobre las 132 preguntas del banco: la identificación
        léxica devolvía una `M*` en **5 preguntas**, y en las cinco el alcance
        resultante quedaba vacío y la consulta caía al respaldo plano. Tomarlas
        como nodo tapaba además al concepto que sí las nombra.

        Un grafo cuya definición no traiga `categoria` —los que arman las
        pruebas— devuelve aquí todos sus nodos, que es lo correcto: sin la marca
        no hay concepción errónea que excluir.
        """
        return tuple(
            i for i in self.identificadores()
            if self._nodos[i].categoria != CATEGORIA_MISCONCEPCION
        )

    def nodo(self, identificador: str) -> Nodo | None:
        """El nodo, o `None` si no está. No lanza: no encontrarlo es normal."""
        return self._nodos.get(identificador)

    def vecinos(self, identificador: str, tipo: str | None = None) -> tuple[str, ...]:
        """Sucesores del nodo, opcionalmente filtrados por tipo de arista.

        Devuelve **tupla vacía** si el nodo no existe, y esto no es descuido:
        `ADR-002` adoptó la configuración D *con respaldo automático a vectorial
        puro cuando no se identifica nodo de entrada*, y `R-17` documenta que esa
        identificación falla en el 14,5 %. Si no encontrar nodo fuese excepción,
        el respaldo sería manejo de errores en vez de una rama prevista.
        """
        if identificador not in self._nodos:
            return ()
        vistos: list[str] = []
        for destino, t in self._salientes.get(identificador, []):
            if tipo is not None and t != tipo:
                continue
            if destino not in vistos:
                vistos.append(destino)
        return tuple(vistos)

    def concepciones_de(self, identificador: str) -> tuple[str, ...]:
        """Concepciones erróneas asociadas al nodo, por la arista de `ADR-006`."""
        return self.vecinos(identificador, tipo=MISCONCEPCION)
