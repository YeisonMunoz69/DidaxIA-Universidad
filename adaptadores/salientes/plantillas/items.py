"""
items.py — Lee el ítem de dos niveles de `p-two-tier.md` (`PM-B08`, enganchado)
==============================================================================

`p-two-tier.md` lleva escrito desde el 2026-08-10 el ítem entero de `N08`: el
ejercicio del turno 1 y **las cuatro razones del turno 2 con lo que delata cada
una**. `dominio/diagnostico/clasificador.py` se escribió para exactamente ese
par y nunca lo recibió, porque nada leía el archivo. Esto es lo que lo lee.

Va aparte de `cargador.py` y no dentro · `ADR-001` §6.2
-------------------------------------------------------------
Son dos lecturas distintas del mismo directorio. `cargador.py` extrae
**repertorio de preguntas** de dieciséis archivos con una regla uniforme; esto
extrae **una estructura** de uno solo, con la forma concreta que ese documento
tiene. Fundirlas obligaría a describir el módulo con un «y», que es la señal de
que son dos.

✅ El puente de notación ya no decide · `PM-C15`, 2026-08-14
---------------------------------------------------------------------
El contenido escribe la matemática **en LaTeX**, porque está escrito para la
docente que lo revisa (`DD-13`): *«Deriva $y = \\cos^3 x$»*. El motor simbólico
lee **notación corriente** —`cos(x)^3`—, que es la misma que `ADR-014` §5.2 le
pide al generador.

Hasta el 2026-08-14 traducir entre las dos era de aquí, y era la parte frágil:
**una dependencia de la FORMA en que está escrito, no de lo que dice**, que se
rompe en silencio si el contenido cambia de estilo. Ahora **cada ficha declara
su expresión ya en notación corriente** y `_derivar()` la prefiere; el puente
queda de respaldo para un ítem que no la traiga.

Lo que sostiene la parte que queda, y ninguna es un comentario:

1. `_a_notacion_corriente()` devuelve **cadena vacía** ante cualquier cosa que
   no sepa traducir con certeza —una barra invertida que sobrevive, una llave,
   un `\\frac`— en vez de entregar una expresión aproximada. Un ítem sin
   expresión no es utilizable, y el filtro deja el diagnóstico vacío diciendo
   por qué. **Traducir mal sería peor que no traducir**: corregiría el turno 1
   contra otro ejercicio y el estado saldría al revés.
2. Lo declarado pasa por el mismo `_ADMISIBLE`: venir escrito a mano no le da
   derecho a colarse con LaTeX dentro.
3. `pruebas/unidad/test_items_dos_niveles.py` lee el archivo **real** y
   **deriva las tres expresiones con el motor de verdad**. Si Fabián reescribe
   un enunciado, o si la fila declarada deja de decir lo mismo que el LaTeX de
   al lado, falla ahí y no en un turno de un estudiante.

El puente sigue usándose para el texto de las razones de `N08`, que lleva
matemática en LaTeX dentro. Las de `N14` y `N05` se escribieron ya en notación
corriente, que es la que el estudiante ve.

Qué NO se lee de ese archivo, y no es un olvido
-------------------------------------------------------
**El texto de las cuatro opciones.** Quien lo muestra al estudiante es el
cliente; el dominio solo necesita saber **cuál** eligió y qué delata. Traerlo
gastaría contexto y metería prosa en un tipo del dominio.

✅ **Las otras dos familias de `RC-PED-06` ya no faltan.** Hasta el 2026-08-14
`N14` (trigonométricas) y `N05` (constantes simbólicas) estaban declaradas en
una tabla, con su nodo y su ítem, pero **sin las cuatro razones**, que es lo
único que hace diagnosticable un ítem. `PM-C15` las escribió y este módulo pasó
a leer **una sección por ítem** en vez del archivo entero de una vez: con tres
ítems, el barrido único metía las doce opciones en el mismo y nada fallaba.


"""

from __future__ import annotations

import re

from dominio.diagnostico.clasificador import OpcionRazon
from dominio.puertos.plantillas import ItemDosNiveles

#: Cada ítem vive en su propia sección `### …`. Se parte por ahí y no se lee
#: el archivo entero de una vez, que es lo que hacía la primera versión cuando
#: solo había un ítem escrito: con tres, un único barrido metería **las doce
#: opciones en el mismo ítem** sin que nada fallara — el `N08` saldría con
#: razones de constantes simbólicas dentro y la parrilla seguiría cuadrando.
_SECCION = re.compile(r"^###\s+", re.M)

#: `| **Nodo** | `N08` |` — la ficha de la sección. Es la fila del ÍTEM, no la
#: de «nodo obligatorio» de la cabecera del archivo: aquélla dice cuál exige
#: `RC-PED-06` como mínimo y no cuál describe cada sección.
_NODO_DE_SECCION = re.compile(r"\|\s*\*\*Nodo\*\*\s*\|\s*`(N\d{2})`", re.I)

#: `| **Expresión, en notación corriente** | `cos(x)^3` |` — lo que el motor
#: sabe leer, escrito por el contenido en vez de traducido por el camino. Ver
#: la cabecera del módulo: mientras esta fila esté, el puente no decide nada.
_CORRIENTE = re.compile(r"notaci[óo]n\s+corriente\*\*\s*\|\s*`([^`]+)`", re.I)

#: El enunciado del turno 1 va en cita en bloque, con la expresión entre `$…$`.
#: Se toma la PRIMERA cita de la sección entera: ahí es donde se pide «escribe
#: solo el resultado».
_PRIMERA_CITA = re.compile(r"^>\s*(.+)$", re.M)

#: Cualquier fórmula de las que el contenido escribe entre `$…$`.
_FORMULA = re.compile(r"\$([^$]+)\$")

#: `| **a** | *«…»* | Razón correcta |` — una fila de opción es la que empieza
#: por una letra suelta en negrita. Las filas de las otras tablas del archivo
#: («| Compuestas | `N08` | …») no casan, que es justo lo que hace falta.
_FILA_DE_OPCION = re.compile(r"^\|\s*\*\*([a-z])\*\*\s*\|(.*)$", re.M)

#: La cita en comillas angulares, que es como este proyecto cita el habla. Se
#: declara aquí y no se importa de `cargador.py`: aquél la usa para extraer el
#: **repertorio de preguntas** y éste para **desenvolver una celda**, que son
#: dos usos que pueden divergir sin que ninguno esté mal.
_ENTRECOMILLADO = re.compile(r"«([^»]+)»")

#: Lo que delata una opción, en el catálogo `M01`–`M24` que el contenido usa.
#: La correcta no nombra ninguna, y esa ausencia ES la señal: `p-two-tier.md`
#: dice que cada razón incorrecta está escrita para delatar una concreta.
_CONCEPCION = re.compile(r"\bM(\d{2})\b")

# ── El puente de notación · ver la cabecera ────────────────────────────────

#: Las funciones que el contenido escribe con barra invertida, y cómo las
#: nombra el analizador del motor (`adaptadores/salientes/simbolico/`).
_FUNCIONES = {
    r"\sin": "sen", r"\cos": "cos", r"\tan": "tan",
    r"\ln": "ln", r"\log": "log", r"\sqrt": "sqrt",
}

#: Adornos de LaTeX que no cambian el significado y se pueden quitar enteros.
_ADORNOS = (r"\left", r"\right", r"\,", r"\;", r"\!", r"\ ")

#: `cos^3 x` → `cos(x)^3`. El exponente va sobre la función, no sobre el
#: argumento: confundirlos convierte `cos^3 x` en `cos(x^3)`, que es
#: **exactamente** la distinción que `M21` mide (ver `c-m21.md`).
_POTENCIA_DE_FUNCION = re.compile(
    r"\b(sen|sin|cos|tan|ln|log)\^\{?(\d+)\}?\s*([a-zA-Z])(?![\w(])"
)

#: `cos x` → `cos(x)`, ya sin exponente de por medio.
_FUNCION_SIN_PARENTESIS = re.compile(r"\b(sen|sin|cos|tan|ln|log)\s+([a-zA-Z])(?![\w(])")

#: `sen(x) cos(x)` → `sen(x)*cos(x)`, `a x^2` → `a*x^2`. La yuxtaposición es
#: producto en la escritura matemática y no lo es para el analizador.
_YUXTAPOSICION = re.compile(r"(?<=[\w)\]])\s+(?=[\w(\[])")

#: Lo único que se admite en la salida. Cualquier otro carácter significa que
#: quedó LaTeX sin traducir, y entonces no se entrega nada — ver la cabecera.
_ADMISIBLE = re.compile(r"^[A-Za-z0-9+\-*/^() ]+$")


def _a_notacion_corriente(formula: str) -> str:
    """`y = \\cos^3 x` → `cos(x)^3`, o cadena vacía si no está seguro.

    Vacío y no aproximado: ver el punto 1 de la cabecera del módulo.
    """
    texto = formula.strip()
    # `y = …` / `f(x) = …`: al motor se le da lo que hay que derivar, no la
    # ecuación que lo nombra. Con más de un `=` no se sabe cuál es, y no se
    # adivina.
    if texto.count("=") == 1:
        texto = texto.split("=", 1)[1]
    for adorno in _ADORNOS:
        texto = texto.replace(adorno, " ")
    for latex, corriente in _FUNCIONES.items():
        texto = texto.replace(latex, corriente)

    texto = _POTENCIA_DE_FUNCION.sub(r"\1(\3)^\2", texto)
    texto = _FUNCION_SIN_PARENTESIS.sub(r"\1(\2)", texto)
    texto = _YUXTAPOSICION.sub("*", texto)
    texto = " ".join(texto.split())

    if not texto or not _ADMISIBLE.match(texto):
        return ""
    return texto


# ── La lectura del documento ────────────────────────────────────────────────


def _sin_latex(texto: str) -> str:
    """El texto con toda su matemática pasada a notación corriente.

    🐛 **Se vio en la salida real, no en una prueba.** La primera versión de
    `PM-B28` emitió al estudiante las razones tal cual venían del archivo, y
    dos de las cuatro llevaban LaTeX dentro: *«Derivé la potencia y multipliqué
    por `$\\sin x$`»*. En pantalla eso son cuatro caracteres de sintaxis y una
    barra invertida, y el estudiante tiene que elegir entre razones de las que
    una está en otro idioma.

    Devuelve **cadena vacía si alguna fórmula no se sabe traducir**, y entonces
    la razón se queda sin texto y el ítem deja de ser ofrecible. Es la misma
    disciplina que `derivar` y `enunciado` siguen: enseñar `$\\frac{1}{x}$` a
    medias es peor que no plantear el ítem.
    """
    salida = texto
    for formula in _FORMULA.findall(texto):
        corriente = _a_notacion_corriente(formula)
        if not corriente:
            return ""
        salida = salida.replace(f"${formula}$", corriente)
    return salida


def _limpiar(celda: str) -> str:
    """El texto de una celda, sin el adorno de Markdown y sin LaTeX.

    Las opciones van escritas como `*«…»*`: cursiva y comillas angulares, que
    es como este proyecto cita el habla. Se quitan las dos —son formato del
    documento, no parte de lo que el estudiante lee— y la matemática de dentro
    se pasa a notación corriente con `_sin_latex`.
    """
    limpia = " ".join(celda.split()).strip()
    for adorno in ("**", "`"):
        limpia = limpia.replace(adorno, "")
    entrecomillada = _ENTRECOMILLADO.search(limpia)
    if entrecomillada is not None:
        limpia = entrecomillada.group(1)
    # La cursiva se quita DESPUÉS de desenvolver las comillas: `*«…»*` deja un
    # asterisco a cada lado, pero un `*` dentro del texto no existe en este
    # contenido y quitarlo antes rompería una expresión como `2*x`.
    return _sin_latex(limpia.strip("* ").strip())


def _opciones(texto: str) -> tuple[OpcionRazon, ...]:
    """Las cuatro razones del turno 2, con su texto y con lo que delata cada una.

    `es_correcta` se decide por **ausencia de concepción** y no por buscar la
    palabra «correcta»: el archivo describe cada opción en prosa libre —«Razón
    correcta», «`M21` · no ve la composición»— y la propiedad que sí es
    estable es la que `p-two-tier.md` declara como regla, *«cada una está
    escrita para delatar una concepción concreta»*. La que no delata ninguna
    es la buena.

    El texto se trae desde `PM-B28`, que es cuando apareció quien lo muestra.
    Hasta entonces no se traía a propósito —el dominio solo necesitaba saber
    cuál se eligió— y era la decisión correcta con lo que había.
    """
    salida: list[OpcionRazon] = []
    for letra, resto in _FILA_DE_OPCION.findall(texto):
        celdas = [c.strip() for c in resto.split("|") if c.strip()]
        # La razón va en la primera celda y lo que delata en la última. Con una
        # sola celda no se puede distinguir una de otra, y entonces no se
        # inventa: se queda sin texto y el ítem deja de ser ofrecible.
        delata = _CONCEPCION.search(celdas[-1]) if celdas else None
        salida.append(
            OpcionRazon(
                identificador=letra,
                es_correcta=delata is None,
                concepcion=f"M{delata.group(1)}" if delata else None,
                texto=_limpiar(celdas[0]) if len(celdas) >= 2 else "",
            )
        )
    return tuple(salida)


def _enunciado(texto: str) -> str:
    """Lo que se le pide al estudiante en el turno 1, en notación corriente.

    El contenido lo escribe en LaTeX —*«Deriva $y = \\cos^3 x$. Escribe solo el
    resultado.»*— porque está escrito para la docente que lo revisa. Al
    estudiante se le manda con la fórmula ya traducida, que es la misma
    notación que `ADR-014` §5.2 usa en todo el contrato: dos notaciones en la
    misma pantalla serían dos cosas que aprender en vez de una.

    Vacío si no se pudo traducir, y entonces el ítem no es ofrecible — la
    misma disciplina que `derivar` sigue, y por el mismo motivo.

    🐛 Se toma la línea ENTERA de la cita. La primera versión usaba el mismo
    patrón no codicioso que busca la fórmula, y ese match **termina en el `$`
    de cierre**: el enunciado salía como *«Deriva cos(x)^3»*, sin el «Escribe
    solo el resultado» que es justo lo que distingue el turno 1 del 2.
    """
    cita = _PRIMERA_CITA.search(texto)
    if cita is None:
        return ""
    return _limpiar(cita.group(1))


def _derivar(seccion: str) -> str:
    """La expresión que corrige el turno 1, en notación corriente.

    **Se prefiere la que el contenido declara** —`PM-C15`, 2026-08-14— y solo
    si no está se traduce del LaTeX del enunciado. El orden es el importante:
    mientras la fila esté escrita, el puente frágil de la cabecera no decide
    nada, y el día que alguien escriba un ítem sin ella el sistema sigue
    funcionando en vez de quedarse sin ítem.

    Lo declarado se comprueba igual con `_ADMISIBLE`: una fila con LaTeX
    dentro por descuido tiene que salir vacía, no colarse por venir escrita a
    mano. Confiar en el contenido no es dejar de mirarlo.
    """
    declarada = _CORRIENTE.search(seccion)
    if declarada is not None:
        texto = " ".join(declarada.group(1).split())
        return texto if _ADMISIBLE.match(texto) else ""

    cita = _PRIMERA_CITA.search(seccion)
    formula = _FORMULA.search(cita.group(1)) if cita else None
    return _a_notacion_corriente(formula.group(1)) if formula else ""


def items_desde_texto(texto: str) -> tuple[ItemDosNiveles, ...]:
    """Los ítems de `p-two-tier.md`, uno por sección `###` que declare su nodo.

    Tupla vacía y nunca una excepción: es la misma propiedad que
    `PuertoPlantillas` declara para sus lecturas. El contenido cambia bajo los
    pies del código y un turno no puede caerse porque una plantilla esté a
    medias.

    Una sección sin fila de nodo **se salta en silencio**, y es lo correcto:
    `p-two-tier.md` puede llevar otras secciones `###` que expliquen el formato
    sin describir ningún ítem. Lo que no se hace es adivinar el nodo por el
    título, que sería depender del texto de una cabecera.

    Se devuelven en el orden del archivo. Un nodo repetido lo resuelve quien
    los indexa —`cargador.py`— y no esto: aquí se lee lo que hay escrito.
    """
    salida: list[ItemDosNiveles] = []
    for seccion in _SECCION.split(texto)[1:]:
        nodo = _NODO_DE_SECCION.search(seccion)
        if nodo is None:
            continue
        salida.append(
            ItemDosNiveles(
                nodo=nodo.group(1).upper(),
                derivar=_derivar(seccion),
                opciones=_opciones(seccion),
                enunciado=_enunciado(seccion),
            )
        )
    return tuple(salida)
