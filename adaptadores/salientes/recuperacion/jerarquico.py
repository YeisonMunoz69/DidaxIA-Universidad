"""
jerarquico.py — Recuperación híbrida grafo→vectorial (S8)
==========================================================

Implementa el puerto `PuertoCorpus` con la **configuración D** de `ADR-002`:
*híbrido jerárquico grafo→vectorial, con respaldo a vectorial puro cuando no se
identifica nodo de entrada*, con `k=3` y el umbral de `ADR-006`.

Por qué no se copia `dual_retriever.py`
---------------------------------------
`06-Guia-de-Reutilizacion.md` §3 lo dictamina 🧭 **solo como referencia**, y §6.1
da el motivo con cifras: su rama `ambos` recupera **primero vectorial y después
expande por grafo**, que es la **configuración C** de E01, y su rama por defecto
ni siquiera consulta el grafo, que es la **A**.

| | Acierto@1 | MRR |
|---|---:|---:|
| C · lo que el prototipo implementa | 0,694 | 0,895 |
| **D · lo que `ADR-002` adoptó** | **0,758** | **0,949** |

Y su `top_k` por defecto es 5 donde `ADR-002` fija 3: subir a 5 cuesta 7,6
puntos de precisión y aporta +0,004 de MRR, o sea que las posiciones 4 y 5 son
relleno.

**Lo que sí se hereda de él** es la idea que la guía le reconoce: coordinar
índice y grafo en un solo filtro, y deduplicar. El orden es lo que cambia, y el
orden era la decisión.

Lo que este adaptador NO hace, y es deliberado
----------------------------------------------
**La ruta diagnóstica de `ADR-006` no está implementada.** Esa decisión quedó
🟢 parcial: se adoptó el umbral, y la ruta —usar la arista
`misconception_asociada` cuando el estudiante enuncia una concepción errónea—
**se aplazó con motivo declarado**, porque no se cumplió el criterio que
`ADR-002` había pre-registrado. El grafo ya expone `concepciones_de()` para
cuando esa decisión se cierre; aquí no se llama. Implementarla ahora sería
tomar por código una decisión que el proyecto dejó abierta a propósito.

**Y ahora esa decisión tiene precio medido.** `PM-V04`, 2026-08-09: de las 132
preguntas del banco, la identificación léxica llegaba a una `M*` en cinco
—`Q56`, `Q57`, `Q62`, `Q80`, `Q105`— y en tres de ellas la arista
`misconception_asociada` apunta desde el nodo que el banco da por correcto
(`M4`→`N12` en `Q56` y `Q62`, `M5`→`N08` en `Q57`). Recorrer esa arista hacia
atrás las habría enrutado bien. **No se hace**, por lo mismo de siempre; pero
quien cierre `ADR-006` ya no tiene que estimar lo que gana: son tres preguntas.

Lo que sí cambió el 2026-08-09, y por qué
------------------------------------------
`PM-V04` midió por fin el identificador solo, y el resultado reordenó las
prioridades: **no le falta cobertura, le sobra confianza**. Ver
`identificar_nodo` y `PerfilLexico`.
"""

from __future__ import annotations

import collections
import math
import re
import unicodedata
from collections.abc import Iterable

from adaptadores.salientes.recuperacion.grafo import GrafoEnMemoria
from adaptadores.salientes.recuperacion.indice import Indice
from dominio.puertos.corpus import Fragmento, Recuperacion

#: `ADR-002` §7.8.7 y `RF-RAG-04`. No es configurable por descuido: el análisis
#: de sensibilidad `RV-09` mostró que la decisión es invariante a k, y que 5 solo
#: añade relleno.
K_ADOPTADO = 3

#: `ADR-006` U4: valor inicial **sin respaldo empírico**, declarado como tal y
#: configurable conforme a `RF-ADM-06`. Se calibra en el objetivo 4 con la
#: distribución de puntuaciones de aciertos frente a fallos. Que aparezca aquí
#: como número no lo convierte en un valor medido.
UMBRAL_INICIAL = 0.70

_TERMINO = re.compile(r"[0-9a-záéíóúüñ]+")

#: Términos demasiado frecuentes para identificar un nodo. Sin esta lista,
#: «la derivada de la función» casaría con casi cualquier etiqueta.
_VACIAS = frozenset(
    (
        "de", "la", "el", "los", "las", "un", "una", "y", "o", "en", "para",
        "por", "con", "que", "como", "se", "su", "sus", "del", "al", "es",
        "son", "este", "esta", "esto", "cual", "cuales", "cuando", "donde",
    )
)


def _palabras(texto: str) -> list[str]:
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return [p for p in _TERMINO.findall(plano) if p not in _VACIAS]


def _terminos(texto: str) -> frozenset[str]:
    return frozenset(_palabras(texto))


#: `PM-V04` §2: cuánto tiene que puntuar el nodo ganador frente al segundo para
#: que el perfil léxico se atreva a nombrarlo. **No es un valor calibrado**, y se
#: declara igual que `UMBRAL_INICIAL`. Lo que sí está medido es que **no es un
#: filo**: 2,0 y 3,0 dan exactamente el mismo `acierto_1` (0,470 sobre las 132),
#: de modo que la cifra no cuelga de haber acertado el número.
MARGEN_INICIAL = 2.0


class PerfilLexico:
    """Vocabulario de cada nodo, **derivado de sus fragmentos**, no declarado.

    Por qué existe
    --------------
    La regla que `identificar_nodo` tenía hasta el 2026-08-09 exige que una
    *forma nombrada* del nodo —su etiqueta o uno de sus sinónimos— aparezca
    entera en la pregunta. Medido sobre las 132 preguntas del banco: dispara en
    66 y **acierta 47, precisión 0,712**. En las otras 66 devuelve `None` y la
    consulta cae al respaldo plano. El motivo es de vocabulario, no de
    ingenio: el estudiante escribe *«¿cómo derivo una fracción de dos
    funciones?»* y el grafo dice *«Regla del cociente»*.

    De dónde sale el vocabulario que falta, y por qué no de la mano
    ---------------------------------------------------------------
    **De los fragmentos ya indexados.** Cada uno declara su `nodo_grafo`, así
    que el material del nodo *es* la definición de cómo se habla de él. Es la
    misma disciplina que `verificar-conceptos.py` aplica desde `PM-C03`: el
    vínculo se **deriva**, no se declara.

    Escribir a mano los términos del estudiante estaba descartado por dos
    motivos independientes. El primero es la regla de `NODOS-CANDIDATOS.md`
    §1.bis: un sinónimo **sale de un título que existe en una obra**, y
    «fracción» no titula nada. El segundo es peor: el único sitio donde está
    escrito cómo pregunta un estudiante es **el banco de evaluación**, y sacar
    de ahí el vocabulario sería ajustar el instrumento a su propia medida.

    Un nodo sin fragmentos no tiene perfil, y eso no es un caso que haya que
    tratar: es lo que significa derivarlo del corpus. `N15` y `N12` no aparecen
    aquí porque no tienen material, y acotar a ellos sería garantizar el vacío.

    Qué se midió antes de elegir la fórmula
    ----------------------------------------
    Cuatro criterios sobre el mismo perfil, sobre las 132 preguntas:

    | criterio | acierto de identificación |
    |---|---:|
    | suma de `idf` de los términos que casan | 0,447 |
    | **centroide `tf·idf`** | **0,508** |
    | coseno sobre `tf` logarítmica normalizada | 0,492 |
    | BM25 (`k1`=1,5, `b`=0,75) | 0,492 |

    Los cuatro caen dentro de dos preguntas de diferencia, y esa es la
    conclusión que importa: **el techo lo pone el corpus, no la fórmula**. Se
    toma el centroide por ser el más simple de los cuatro; elegirlo por ser el
    más alto sobre este banco sería ajustar a la propia medida.
    """

    def __init__(self, pesos: dict[str, dict[str, float]]) -> None:
        self._pesos = pesos

    @classmethod
    def desde_fragmentos(cls, fragmentos: Iterable[Fragmento]) -> PerfilLexico:
        """Perfil de los nodos que tienen material, a partir del texto indexado."""
        cuentas: dict[str, collections.Counter] = {}
        for f in fragmentos:
            if f.nodo_grafo:
                cuentas.setdefault(f.nodo_grafo, collections.Counter()).update(
                    _palabras(f.texto)
                )
        if not cuentas:
            return cls({})

        total_nodos = len(cuentas)
        aparece: collections.Counter = collections.Counter()
        for c in cuentas.values():
            aparece.update(c.keys())

        pesos = {}
        for identificador, c in cuentas.items():
            largo = sum(c.values())
            # `tf` relativo al tamaño del nodo por `idf` sobre los nodos. Un
            # término que está en todos los nodos pesa cero y se descarta: no
            # distingue nada y solo añade ruido proporcional a la longitud.
            pesos[identificador] = {
                t: (v / largo) * math.log(total_nodos / aparece[t])
                for t, v in c.items()
                if aparece[t] < total_nodos
            }
        return cls(pesos)

    def __len__(self) -> int:
        return len(self._pesos)

    def nodos(self) -> tuple[str, ...]:
        return tuple(sorted(self._pesos))

    def candidato(self, pregunta: frozenset[str], margen: float) -> str | None:
        """El nodo cuyo vocabulario explica mejor la pregunta, si destaca.

        Devuelve `None` cuando el ganador no supera al segundo por `margen`, y
        eso **no es prudencia decorativa**: medido de punta a punta el
        2026-08-09, dejar que el perfil nombre siempre a su ganador *baja*
        `acierto_1` de 0,447 a 0,432, porque acotar a un nodo equivocado
        recupera peor que no acotar. Exigir margen invierte el signo: 0,470.
        """
        puntos = sorted(
            (
                (sum(pesos.get(t, 0.0) for t in pregunta), identificador)
                for identificador, pesos in self._pesos.items()
            ),
            key=lambda par: (-par[0], par[1]),
        )
        if not puntos or puntos[0][0] <= 0.0:
            return None
        if len(puntos) > 1 and puntos[0][0] < margen * puntos[1][0]:
            return None
        return puntos[0][1]


class RecuperadorJerarquico:
    """Puerto de recuperación de contexto, configuración D.

    El umbral se aplica **aquí** y no en el filtro porque el contrato del puerto
    ya lo dice —`recuperar()` devuelve la recuperación *«con umbral aplicado»*—
    y ese contrato es anterior a este adaptador.

    > **Tensión anotada, no resuelta.** Se puede defender que el umbral es
    > política de dominio y no detalle de almacén, y por tanto que su sitio
    > natural sería el filtro 5. Se respeta el contrato escrito en vez de
    > cambiarlo de paso: el puerto tiene pruebas que dependen de él, y
    > modificar una frontera merece su propia tanda y su motivo, no una
    > decisión colateral. Queda registrado para que sea deliberado.
    """

    def __init__(
        self,
        indice: Indice,
        grafo: GrafoEnMemoria,
        umbral: float = UMBRAL_INICIAL,
        perfil: PerfilLexico | None = None,
        margen: float = MARGEN_INICIAL,
        prerrequisitos: bool = True,
    ) -> None:
        self._indice = indice
        self._grafo = grafo
        self._umbral = umbral
        # `perfil` es opcional **y por defecto no está**: sin él, este adaptador
        # se comporta exactamente como antes del 2026-08-09. Es deliberado. El
        # perfil se deriva del corpus, así que quien lo construye tiene que
        # tener el corpus a mano, y el sitio de esa decisión es la composición
        # de la aplicación, no un adaptador que se arma en una prueba con tres
        # fragmentos inventados.
        self._perfil = perfil
        self._margen = margen
        # Por defecto `True`: es lo que `ADR-002` adoptó. Existe como parámetro
        # para poder medir la alternativa sin duplicar el adaptador dentro del
        # arnés — ver el comentario en `recuperar()`.
        self._prerrequisitos = prerrequisitos
        # Las etiquetas se convierten a términos una sola vez, al construir: la
        # identificación del nodo ocurre en cada turno y está en la ruta
        # caliente, donde `RNF-EFI-01` presupone ≤300 ms para el filtro 3.
        #
        # **Se indexan la etiqueta Y `formas_de_consulta`.** Hasta el 2026-08-08
        # el nodo se identificaba solo por su etiqueta completa, y leer también
        # las otras formas valía once puntos sobre las 62 del banco —22/62
        # frente a 29/62—.
        #
        # ⚠️ **Y desde `PM-C17` la lista que se lee NO es `sinonimos`.** Ese
        # campo es de la cobertura del corpus y se rige por §1.bis —«sale de un
        # título que existe en una obra»—, que es una regla sobre la
        # procedencia. Aquí hace falta otra cosa: que la forma **distinga** este
        # nodo de los demás. `PM-C16` midió que las dos exigencias se separan de
        # verdad en los dos extremos —«diferenciación» cubre 11 unidades y pesa
        # 0,25; «derivada del cociente» no titula nada y gana `Q77`— y `D-25`
        # las repartió en dos listas. Ver `grafo.py`, `Nodo.formas_de_consulta`.
        #
        # **Solo conceptos.** `grafo.conceptos()` deja fuera a `M1`–`M5`: una
        # concepción errónea no es un tema y no tiene material que recuperar.
        # Ver `GrafoEnMemoria.conceptos()` para lo que costaba tomarlas.
        self._formas: dict[str, tuple[frozenset[str], ...]] = {}
        for identificador in grafo.conceptos():
            n = grafo.nodo(identificador)
            if n is None:
                continue
            # La etiqueta va siempre y no se reparte: un nodo al que no se
            # puede llamar por su nombre no se alcanza por ninguna vía, y
            # `PM-V13` midió lo que cuesta callar una forma pobre —7 preguntas
            # dejan de disparar y se pierden 6 aciertos para quitar 1 fallo—.
            # Por eso «Función derivada», que pesa 0,48, sigue enrutando.
            formas = [_terminos(n.etiqueta)]
            formas += [_terminos(s) for s in (n.formas_de_consulta or ())]
            self._formas[identificador] = tuple(f for f in formas if f)
        # Quién es especialización de quién, por la clausura de `prerrequisito_de`.
        # Se calcula una vez al construir, como las formas y por el mismo motivo:
        # `identificar_nodo` está en la ruta caliente. Ver `_por_forma_nombrada`
        # para qué decide.
        self._especializaciones: dict[str, frozenset[str]] = {
            i: self._descendientes(grafo, i) for i in self._formas
        }
        # `PM-V13`: cuánto vale cada término para señalar UN nodo. Ver
        # `_peso_de_forma` sobre por qué esto sustituye a contar términos.
        reparto: dict[str, int] = {}
        for formas in self._formas.values():
            for termino in {t for f in formas for t in f}:
                reparto[termino] = reparto.get(termino, 0) + 1
        self._peso_de_termino: dict[str, float] = {
            t: 1.0 / n for t, n in reparto.items()
        }

    @staticmethod
    def _descendientes(grafo: GrafoEnMemoria, raiz: str) -> frozenset[str]:
        """Todo lo que el grafo deriva de `raiz` siguiendo `prerrequisito_de`."""
        vistos: set[str] = set()
        pila = [raiz]
        while pila:
            for sucesor in grafo.vecinos(pila.pop(), tipo="prerrequisito_de"):
                if sucesor not in vistos:
                    vistos.add(sucesor)
                    pila.append(sucesor)
        return frozenset(vistos)

    # -- identificación léxica del nodo de entrada ------------------------

    def identificar_nodo(self, consulta: str) -> str | None:
        """Nodo de entrada por coincidencia léxica, o `None`.

        **`R-17` mide que esto falla en el 14,5 %**, y que en ese subconjunto el
        acierto cae de 0,792 a 0,556. Devolver `None` no es un error: es la
        entrada de la rama de respaldo, y por eso el riesgo está registrado como
        alto en lugar de mitigado.

        Dos reglas, y el orden importa
        -------------------------------
        1. **Forma nombrada.** La etiqueta o un sinónimo, entero, dentro de la
           pregunta, y la más larga si hay varias. La regla no ha cambiado; lo
           que `PM-V11` cambió el 2026-08-10 es **cómo se rompe el empate**, que
           antes lo decidía la numeración de los nodos — ver `_desempatar`.
        2. **Perfil léxico**, y solo si la 1 no dijo nada y solo cuando el
           ganador destaca por `margen`. Rellena; no corrige.

        Por qué la 2 no puede pisar a la 1
        -----------------------------------
        Porque se midió al revés y salió peor. Dejar que el perfil decidiera
        siempre subió el acierto de identificación de 0,356 a 0,508 y **bajó**
        `acierto_1` de 0,447 a 0,432: acotar a un nodo equivocado recupera peor
        que no acotar, porque el respaldo plano busca sobre el corpus entero y
        una jerarquía mal enrutada busca sobre el trozo que no es. La lección,
        que vale más que el número: **de este identificador hay que exigir
        precisión, no cobertura.**
        """
        pregunta = _terminos(consulta)
        if not pregunta:
            return None
        nombrado = self._por_forma_nombrada(pregunta)
        if nombrado is not None:
            return nombrado
        if self._perfil is None:
            return None
        return self._perfil.candidato(pregunta, self._margen)

    def _peso_de_forma(self, forma: frozenset[str]) -> float:
        """Cuánto señala una forma a UN nodo, y no a cualquiera · `PM-V13`.

        Hasta el 2026-08-14 las formas se ordenaban por **número de términos**, y
        ése era el defecto más caro que quedaba del identificador: `PM-V11`
        repartió los fallos sobre las 132 y **diez** —de los que solo uno cae
        fuera del techo de `DD-23`— eran «forma genérica». Es el tercer
        avistamiento del mismo problema: `«aproximacion lineal»` en `N06`
        (`PM-V04`) y los ocho empates de `PM-V11` fueron los dos primeros.

        El defecto se ve en una línea del propio grafo: quitadas las palabras
        vacías, «Función derivada» es `{funcion, derivada}` — **dos términos que
        aparecen en trece etiquetas y sinónimos entre los dos**—, y con la regla
        de contar valía exactamente lo mismo que `{cociente, incremental}`, que
        no nombra otra cosa en todo el grafo.

        Cada término vale `1 / cuántos nodos lo usan`, y la forma vale la suma.
        Así `{derivada, funcion}` puntúa **0,44** y `{recta, tangente}` **2,00**:
        la longitud sigue contando —cinco términos raros valen más que uno— pero
        **repetir vocabulario común deja de comprar autoridad**.

        Por qué la frecuencia se cuenta sobre EL GRAFO y no sobre el corpus
        -------------------------------------------------------------------
        Porque lo que se mide aquí es *«¿este término distingue un nodo de los
        demás?»*, y eso es una propiedad de cómo están nombrados los nodos. La
        frecuencia en el corpus es otra cosa —la mide `PerfilLexico`, que es la
        regla 2— y mezclarlas haría que **cambiar el corpus moviera el
        enrutamiento sin que nadie tocara el grafo**.

        Lo que NO es, y `PM-V12` lo dejó medido
        ----------------------------------------
        No es ampliar vocabulario: añadir sinónimos a `N08` y `N11` no movió
        nada, y limpiar el LaTeX del perfil **empeoró** (0,691 → 0,684). Esto no
        añade ni quita términos; cambia **quién gana** entre los que ya casaban.

        ⛔ Lo que se probó DESPUÉS y se descartó, con su cifra
        ------------------------------------------------------
        Ordenar por peso deja los diez fallos por forma genérica en diez, porque
        esas seis formas pobres no ganan compitiendo: ganan **cuando no compite
        ninguna otra**. Contra eso se midieron dos mecanismos más, sobre las 132
        y con el índice real (2026-08-14):

        | variante | precisión | sobre alcanzables | precision_k | recall_nodo | genérica |
        |---|---:|---:|---:|---:|---:|
        | contar términos *(hasta hoy)* | 0,691 | 0,714 | 0,561 | 0,599 | 10 |
        | **peso, adoptada** | **0,701** | **0,726** | **0,571** | **0,614** | 10 |
        | peso + piso 0,55 | 0,702 | 0,728 | 0,568 | 0,606 | 9 |
        | peso + piso 0,70 | 0,699 | 0,725 | 0,563 | 0,606 | 9 |
        | peso + piso 1,00 | 0,689 | 0,714 | 0,561 | 0,606 | 9 |
        | peso + ceder al perfil bajo 1,00 | 0,701 | 0,726 | 0,571 | 0,614 | 10 |

        **Un piso —callar la forma pobre— cuesta más de lo que ahorra.** Con
        `1,0`, que es el único valor con lectura —*«valer al menos un término que
        no nombre a ningún otro nodo»*— el identificador deja de disparar en 7
        preguntas y **pierde 6 aciertos para quitar 1 fallo**. Los pisos
        intermedios recortan un fallo genérico y bajan la recuperación igual, y
        `0,55` es un número elegido por su pico en este banco: adoptarlo sería
        ajustar el criterio a la medida, que es lo que `D-11` se cuidó de evitar.

        **Y hacer que la forma pobre CEDA ante el perfil, en vez de callar, no
        cambia una sola cifra.** Eso no es que la idea sea mala: es que en esas
        preguntas el perfil léxico **tampoco tiene candidato con margen**. Dicho
        de otro modo, la evidencia no está ni en el nombre ni en el corpus, que
        es la misma frontera que `PM-V12` describió para «ninguna palabra a
        favor». `acierto_1` se queda en 0,515 en las seis variantes.

        Y lo que este peso decide ADEMÁS, desde `PM-C17`
        -------------------------------------------------
        Reparte el contenido: `D-25` separó `sinonimos` —cobertura del corpus—
        de `formas_de_consulta` —enrutamiento—, y **el criterio para repartir
        las formas que ya existían es este peso**, calculado sobre el grafo. Que
        se compute sobre el grafo es justo lo que lo hace admisible: clasificar
        con él no mira ni una pregunta del banco, así que no es ajustar el
        contenido a su propia medida.

        ⚠️ **Y el piso de ese reparto no es ninguno de los cuatro de la tabla de
        arriba.** Son dos mecanismos distintos y conviene no confundirlos:

        - Aquellos **callaban toda forma** bajo el umbral, **etiqueta incluida**,
          y por eso salían caros: sin ninguna forma que casar, la pregunta deja
          de disparar y cae al respaldo plano.
        - El reparto solo mueve **sinónimos**. La etiqueta enruta siempre.

        Con el piso en **0,50** —*«valer al menos un término que solo comparta
        con otro nodo»*— la única forma que sale del enrutamiento es
        «diferenciación», que pesa 0,25. Es un subconjunto estricto de lo que
        callaba el piso 0,55, el más suave que se midió.
        """
        return sum(self._peso_de_termino.get(t, 1.0) for t in forma)

    def _por_forma_nombrada(self, pregunta: frozenset[str]) -> str | None:
        """Regla 1: la etiqueta o un sinónimo, entero, dentro de la pregunta.

        Gana la forma que más señala —ver `_peso_de_forma`, `PM-V13`— y **el
        empate lo rompe el grafo**: ver `_desempatar`.
        """
        mejor: dict[str, float] = {}
        for identificador, formas in self._formas.items():
            for forma in formas:
                # Se exige cubrir la forma entera: «derivada» no debe activar
                # «Derivada en un punto», que es un nodo distinto y más
                # específico. Y una forma puede no ser la etiqueta: el
                # estudiante dice «tasa de variación» donde el grafo dice «Tasa
                # de cambio», y hasta el 2026-08-08 eso no identificaba nada.
                if forma <= pregunta:
                    peso = self._peso_de_forma(forma)
                    if peso > mejor.get(identificador, 0.0):
                        mejor[identificador] = peso
        if not mejor:
            return None
        # Se redondea antes de comparar: dos formas de pesos como 1/3+1/3+1/3 y
        # 1/2+1/2 pueden salir separadas por 1e-16 y entonces el empate —que
        # `_desempatar` existe para resolver con el grafo— no llegaría nunca a
        # detectarse. Seis decimales están muy por debajo de cualquier
        # diferencia con significado, porque el peso más pequeño posible es
        # `1/25`.
        cima = max(mejor.values())
        empatados = [i for i, p in mejor.items() if round(p, 6) == round(cima, 6)]
        if len(empatados) == 1:
            return empatados[0]
        return self._desempatar(empatados)

    def _desempatar(self, empatados: list[str]) -> str:
        """Entre nodos igual de nombrados, gana la especialización.

        Por qué hace falta un criterio, y por qué éste
        ----------------------------------------------
        Hasta el 2026-08-10 el empate lo rompía **el orden de inserción del
        diccionario**, es decir, la numeración de los nodos: `N04` ganaba a `N05`
        y `N05` a `N15` porque `PM-C09` los numeró en ese orden. `PM-V11` repartió
        los 34 fallos de identificación sobre las 132 preguntas y **ocho eran
        empates a dos términos**, de modo que un octavo del error lo decidía algo
        que no significa nada.

        Los empates existen porque tres etiquetas del grafo, quitadas las palabras
        vacías, se reducen a la misma pareja genérica: «Derivada en un punto» es
        `{derivada, punto}` y «Función derivada» es `{funcion, derivada}`. Es el
        defecto de «aproximación lineal» en `N06` que `PM-V04` encontró una vez, y
        tenía hermanos.

        Se elige la especialización —el nodo que el grafo deriva del otro por
        `prerrequisito_de`— **por lo que la configuración D hace después con el
        nodo**, no por lo que acierta sobre este banco:

            alcance = (entrada,) + vecinos(entrada, "prerrequisito_de")

        `N05` tiene **diez** sucesores directos, así que nombrarlo acota a once
        nodos: casi el corpus entero. `N15` no tiene ninguno. Ante la misma
        evidencia léxica, el general no acota y el específico sí, y acotar es la
        única razón por la que el grafo va delante del vectorial.

        Medido: la precisión del identificador pasa de 0,649 a 0,691. Arregla seis
        preguntas y rompe dos —`Q06` y `Q59`, las dos del par `N04`/`N05`, que
        ninguna regla léxica separa porque nombran los dos conceptos—. Que rompa
        algo se dice aquí y no solo en la bitácora.

        Si el empate no es entre un nodo y su descendiente —dos ramas hermanas—,
        no hay nada que el grafo diga, y se conserva el orden anterior en vez de
        inventar un criterio.
        """
        for i in empatados:
            if all(i in self._especializaciones[j] for j in empatados if j != i):
                return i
        orden = list(self._formas)
        return min(empatados, key=orden.index)

    # -- puerto ------------------------------------------------------------

    def recuperar(
        self,
        consulta: str,
        nodo: str | None = None,
        k: int = K_ADOPTADO,
    ) -> Recuperacion:
        """Recupera fragmentos con la jerarquía de `ADR-002` y el umbral de `ADR-006`."""
        entrada = nodo or self.identificar_nodo(consulta)

        if entrada is not None and self._grafo.nodo(entrada) is not None:
            # Configuración D: **el grafo acota primero**. El alcance es el nodo
            # y sus prerrequisitos, que es lo que `T5` adoptó para que el grafo
            # enrute sin que el índice crezca con él.
            #
            # ⚠️ **Y los prerrequisitos son hoy el defecto más caro que tiene el
            # sistema.** `PM-V04`, 2026-08-09, banco de 132 contra el índice
            # real: dándole al recuperador el nodo correcto de antemano,
            # `acierto_1` es **0,667 con prerrequisitos y 0,833 sin ellos** —el
            # techo del banco es 0,841—. Sin dárselo, 0,455 frente a 0,500. El
            # `recall_nodo` no baja al quitarlos: sube. Diluyen el primer puesto
            # con material del prerrequisito.
            #
            # **No se cambia aquí.** El alcance con prerrequisitos es lo que
            # `ADR-002` adoptó citando a `T5`, y voltearlo desde el código sería
            # cerrar por implementación una decisión de arquitectura. Lo que sí
            # se hace es dejarlo **medible**: `prerrequisitos=False` reproduce la
            # cifra de arriba, igual que `umbral=0.0` reproduce la variante 2 del
            # diagnóstico. Quien tome la decisión no tendrá que estimar.
            alcance = (entrada,)
            if self._prerrequisitos:
                alcance += self._grafo.vecinos(entrada, tipo="prerrequisito_de")
            candidatos = self._indice.similares(consulta, k=k, nodos=alcance)
            # Respaldo dentro de la rama con nodo: si acotar deja la consulta sin
            # nada, se vuelve a preguntar sin acotar. Sin esto, identificar el
            # nodo podría dar PEOR resultado que no identificarlo, que es lo
            # contrario de lo que la configuración D pretende.
            if not candidatos:
                candidatos = self._indice.similares(consulta, k=k)
        else:
            # Respaldo a vectorial puro. `ADR-002` lo adoptó explícitamente
            # *«cuando no se identifica nodo de entrada»*.
            candidatos = self._indice.similares(consulta, k=k)

        admitidos = tuple((f, s) for f, s in candidatos if s >= self._umbral)

        if not admitidos:
            # `ADR-006` U3 · modo sin fuente. U2 es explícito en que el mínimo de
            # tres de `RF-RAG-03` cede ante el umbral: **más vale sin contexto
            # que con contexto irrelevante**.
            return Recuperacion(fragmentos=(), similitudes=(), sin_fuente=True)

        return Recuperacion(
            fragmentos=tuple(f for f, _ in admitidos),
            similitudes=tuple(s for _, s in admitidos),
            sin_fuente=False,
        )
