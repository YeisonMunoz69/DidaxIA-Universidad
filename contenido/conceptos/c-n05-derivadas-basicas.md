# C-N05-derivadas-basicas · Las que hay que tener de memoria, y por qué esas

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-N05-derivadas-basicas` |
| **Nodo del grafo** | `N05` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

Un puñado corto de derivadas que se usan como piezas en todo lo demás: la constante, la
identidad, la potencia, el seno y el coseno, la exponencial y el logaritmo.

**No es una lista para memorizar sin más.** Cada una de ellas se dedujo de la definición o
de una regla anterior, y saber de dónde sale cada una es lo que permite reconstruirla
cuando se olvida.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Aplicar bien la regla de la cadena y equivocarse en la derivada de dentro, con lo que el
  resultado parece un fallo de la cadena y no lo es
- Escribir la derivada del coseno sin el signo menos
- Derivar $a^x$ como si fuera $x^n$, bajando el exponente
- Dudar de la derivada de una constante y dejarla escrita en vez de anular el sumando

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

| Concepto previo | Por qué |
|---|---|
| `C-variable-de-derivacion` | Media lista deja de tener sentido si no está decidido respecto de qué se deriva: $a^x$ y $x^a$ se distinguen justo ahí |
| `C-pendiente-como-derivada` | Las básicas se deducen de la definición, que es una pendiente; sin eso la lista es arbitraria |

## La explicación

La lista tiene un orden que no es alfabético: **cada entrada se apoya en la anterior**. La
constante y la identidad salen directamente de la definición. La potencia sale de esas dos
por inducción y por la regla del producto. Las trigonométricas salen de la definición con
las identidades de suma de ángulos. La exponencial y el logaritmo salen la una de la otra.

Por eso la manera de estudiarla no es repetirla: es **poder decir de dónde sale cada
línea**. Quien puede reconstruir dos o tres ya no necesita confiar en la memoria para las
demás.

Y hay una consecuencia práctica: cuando un resultado sale raro, el primer sitio donde
mirar **no es la regla grande sino la pieza pequeña**. La mayoría de los errores en una
cadena o un producto están en la derivada básica de dentro.

## Qué muestra la simulación

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- La tabla de básicas donde **cada fila se puede desplegar** y muestra su deducción, no
  solo su resultado.
- Cada función y su derivada **superpuestas**: se ve que donde la primera sube, la segunda
  es positiva.
- Un modo comparación entre $x^a$ y $a^x$ con un deslizador para $a$, para que la
  diferencia entre base y exponente sea visible y no una regla que se recuerda.
- Un ejercicio de cadena con la derivada interna **elegible de la tabla**, para que se vea
  qué pieza se está usando.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M22`
y `C-M23` lo declaraban como prerrequisito y el banco no lo tenía.

El corpus lo cubre de sobra desde `PM-C07`: las reglas básicas están en `PUR`, `LEI`, `SPI`
y `PIS`, y la exponencial y el logaritmo entraron con `PIS` §8, §10 y §12.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
