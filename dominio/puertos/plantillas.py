"""
plantillas.py — Puerto del andamiaje socrático (S9 · `PM-B06` · `RC-PED-01`…)
=====================================================================================

El quinto puerto de `ADR-001` §6.2. Existe porque `contenido/plantillas/`
—dieciséis archivos escritos por `PM-C14` el 2026-08-10— **no tenía quien los
leyera**: el filtro 7 mandaba al generador tres líneas de andamio genérico
mientras la pedagogía del trabajo de grado esperaba en disco.

La pregunta que este puerto contesta, y la que NO
--------------------------------------------------------
Contesta **«dame el andamiaje de esta situación pedagógica»**, en los términos
del dominio: una concepción del catálogo `M01`–`M24`, o una clase de
andamiaje. No contesta «dame el archivo `s-m21.md`» ni «dame este Markdown»:
si este puerto hablara de rutas o de formatos, el dominio estaría decidiendo
cómo se guarda el contenido, que es justo lo que `ADR-001` §6.2 le prohíbe.

**Quién elige es el filtro, no el adaptador.** El puerto sirve piezas; la
regla de qué pieza toca en qué situación es pedagogía y vive en
`dominio/filtros/prompt.py`, donde se puede leer como una tabla. Ponerla en el
adaptador la escondería detrás del sistema de archivos.

Por qué `Plantilla` lleva preguntas y no el documento entero
--------------------------------------------------------------------
Un archivo de `contenido/plantillas/` está escrito **para una docente que lo
revisa**: trae su tabla de metadatos, la traza a su `RC-PED-`, el estado de
revisión y una sección «lo que esta plantilla no hace». Nada de eso le sirve
al generador, y mandárselo entero gastaría contexto en prosa que no cambia lo
que pregunta.

Lo que sí le sirve son **las preguntas**, que en todos los archivos van
marcadas con `«…»` — es la convención que `PM-C14` ya siguió, no una que este
puerto imponga. `Plantilla.preguntas` son esas, y `titulo` sitúa de qué
andamiaje salieron.

La regla que este puerto hereda del contenido, y no puede romper
------------------------------------------------------------------------
`contenido/plantillas/LEEME.md` §«La regla que gobierna todas»: **ninguna
ranura admite el resultado del ejercicio**. Las plantillas son preguntas y
casos de contraste; el desarrollo precalculado sigue entrando por la
orientación privada del filtro 7, truncado, que es donde `R-22` lo vigila.
Este puerto no relaja esa frontera: sirve preguntas, no respuestas.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dominio.diagnostico.clasificador import OpcionRazon

#: Las cinco clases de andamiaje de `contenido/plantillas/`, nombradas por lo
#: que HACEN y no por su archivo. El adaptador traduce cada clave al `p-….md`
#: que le corresponda; el dominio nunca escribe un nombre de archivo.
#:
#: `RC-PED-01`. Andamiaje por transición de nivel APOS — para cuando no hay
#: error que remediar sino un salto de nivel que acompañar.
SOCRATICA_APOS = "socratica-apos"
#: `RC-PED-02`. Los cinco pasos KQ1–KQ5, para cuando el estudiante YA escribió
#: algo que se le puede señalar.
SCAFFOLDING_KQ = "scaffolding-kq"
#: `RC-PED-06`. El ítem de dos turnos: primero el resultado, luego la razón.
TWO_TIER = "two-tier"
#: `RC-PED-19`. Retroalimentación que nombra la capacidad, no el resultado.
AUTOCONCEPTO = "autoconcepto"
#: `RC-PED-20`. Estrategia y comprobación, para el que no sabe por dónde empezar.
AUTORREGULACION = "autorregulacion"

CLAVES = (SOCRATICA_APOS, SCAFFOLDING_KQ, TWO_TIER, AUTOCONCEPTO, AUTORREGULACION)


@dataclass(frozen=True)
class Plantilla:
    """Un andamiaje, en lo que el generador necesita de él.

    `preguntas` son las que el contenido marcó con `«…»`. Puede venir vacía
    —una plantilla existe y no tiene ninguna citada así— y eso **no es un
    error**: quien la use decide si con eso vale, igual que
    `Recuperacion.utilizable` decide sobre los fragmentos.
    """

    clave: str
    titulo: str
    preguntas: tuple[str, ...] = ()
    #: `D-5`, fase 4 · por qué esta plantilla no trajo repertorio, cuando no lo
    #: trajo. Vacío es lo normal. Existe para que un contenido mal delimitado
    #: **se note** en vez de degradar en silencio: quien la sirve lo publica en
    #: `/api/salud` y quien la consume puede decirlo en su traza.
    diagnostico: str = ""

    @property
    def utilizable(self) -> bool:
        """Si aporta algo al prompt. Una plantilla sin preguntas no aporta:
        su prosa es para la docente que la revisa, no para el generador."""
        return bool(self.preguntas)


@dataclass(frozen=True)
class ItemDosNiveles:
    """El ítem de `RC-PED-06` de un nodo, tal como el contenido lo escribió.

    `p-two-tier.md` §La plantilla lo declara entero: un ejercicio del que se
    pide **solo el resultado**, y cuatro razones de las que **cada una está
    escrita para delatar una concepción concreta**. Este tipo es esas dos
    cosas y nada más — el texto de las opciones no viaja porque quien lo
    muestra es el cliente, y el dominio solo necesita saber cuál se eligió.

    ⚠️ `derivar` es la expresión **en notación corriente**, la que el motor
    simbólico sabe leer. El contenido la escribe en LaTeX para la docente que
    lo revisa, así que traducirla es del adaptador — igual que los nombres de
    archivo. Vacía cuando no se pudo traducir, y entonces `utilizable` es
    falso: sin ella no hay forma de comprobar el turno 1, y **un ítem que no
    se puede corregir no se usa a medias**.
    """

    nodo: str
    derivar: str = ""
    opciones: tuple[OpcionRazon, ...] = ()
    #: `PM-B28` · lo que se le pide al estudiante en el turno 1, tal como el
    #: contenido lo escribió y con la fórmula ya en notación corriente. Vacío
    #: si el banco no lo trajo, y entonces el ítem no es **ofrecible** aunque
    #: siga siendo clasificable — ver las dos propiedades de abajo.
    enunciado: str = ""

    @property
    def utilizable(self) -> bool:
        """Si con esto se puede **diagnosticar** de verdad.

        Hacen falta las dos mitades: la expresión que corrige el turno 1 y al
        menos dos opciones —una correcta y una que delate algo—, porque con
        una sola la parrilla 2×2 de `p-two-tier.md` se queda en una fila.
        """
        return bool(self.derivar) and len(self.opciones) >= 2

    @property
    def ofrecible(self) -> bool:
        """Si además se le puede **plantear** a alguien.

        Son dos preguntas distintas y se separan a propósito: clasificar
        necesita saber qué delata cada opción; ofrecer necesita el enunciado y
        el texto de todas ellas. Un ítem del que se perdiera un texto se puede
        seguir corrigiendo, pero mostrarlo dejaría una opción en blanco — y una
        opción vacía no es una razón que nadie pueda elegir.
        """
        return (
            self.utilizable
            and bool(self.enunciado)
            and all(o.texto for o in self.opciones)
        )

    def opcion(self, identificador: str) -> OpcionRazon | None:
        """La opción que el estudiante eligió, o `None` si no es del ítem.

        `None` y no una opción inventada: una razón que el banco no reconoce
        no delata nada, y `p-two-tier.md` es explícito en que una razón que no
        delata convierte el ítem en adivinanza.
        """
        clave = identificador.strip().lower()
        return next((o for o in self.opciones if o.identificador == clave), None)


@runtime_checkable
class PuertoPlantillas(Protocol):
    """Contrato del andamiaje socrático. Dónde vive el contenido —archivos,
    base, servicio— es del adaptador.

    Las dos operaciones son **lecturas y nunca fallan**: devuelven `None`
    cuando no hay pieza para esa situación. Es deliberado y es la propiedad
    que el filtro 7 necesita: `contenido/` cambia bajo los pies del código
    —Fabián escribe secuencias nuevas, las docentes corrigen— y un turno no
    puede caerse porque una concepción todavía no tenga la suya.
    """

    def secuencia_de(self, concepcion: str) -> Plantilla | None:
        """La remediación de UNA concepción del catálogo (`M01`–`M24`).

        `None` si esa concepción no tiene secuencia escrita — hoy hay once de
        veinticuatro, y las trece que faltan no son un defecto: `PM-C14` cubrió
        las del alcance v1.
        """
        ...

    def plantilla(self, clave: str) -> Plantilla | None:
        """El andamiaje genérico de una de las `CLAVES`.

        `None` si esa clase no está escrita. Quien pregunte decide con qué
        seguir; este puerto no inventa un sustituto.
        """
        ...

    def nodo_del_ejercicio(self, expresion: str) -> str | None:
        """El nodo cuyo ítem plantea **exactamente este ejercicio**, o `None`.

        🔴 **Fase 4 R1 · paquete B.** Es la vuelta de `item_de()`, y existe
        porque el enrutamiento léxico se equivocaba de familia en el caso que
        `RC-PED-06` nombra primero: `cos(x)^3` iba a `N14` —«derivadas de
        funciones trigonométricas»— porque el perfil léxico ve «cos» y ése es
        el nodo que más lo usa. El tutor acababa planteando *«Deriva
        sen(x)·cos(x)»* a quien preguntaba por `cos(x)^3`.

        **No es una excepción de texto.** `p-two-tier.md` ya declara, por
        nodo y en notación corriente, cuál es el ejercicio de cada ítem
        —`cos(x)^3` para `N08`, `sen(x)*cos(x)` para `N14`, `a*x^2 + k` para
        `N05`—. Preguntarle al contenido qué nodo plantea el ejercicio que el
        estudiante escribió es leer una declaración que ya existe; escribir
        aquí una lista de expresiones sería inventar una segunda.

        `None` cuando ningún ítem plantea esa expresión, que es el caso
        normal: el enrutamiento léxico sigue siendo quien decide entonces.
        """
        ...

    def item_de(self, nodo: str) -> ItemDosNiveles | None:
        """El ítem de dos niveles escrito para ese nodo del grafo.

        `None` cuando ese nodo no tiene ítem. Desde `PM-C15` (2026-08-14) lo
        tienen los tres que `RC-PED-06` nombra —`N08` compuestas, `N14`
        trigonométricas y `N05` constantes simbólicas—; los otros veintidós
        nodos del grafo no, y devolver `None` es decirlo en vez de taparlo.
        """
        ...
