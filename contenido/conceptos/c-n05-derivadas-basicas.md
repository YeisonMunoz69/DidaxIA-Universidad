# C-N05-derivadas-basicas · Las que hay que tener de memoria, y por qué esas

| | |
|---|---|
| **Identificador** | `C-N05-derivadas-basicas` |
| **Nodo del grafo** | `N05` |
| **Concepción errónea asociada** | `— · **no es una concepción errónea, es un prerrequisito**` |
| **Estado** | Borrador · pendiente de revisión docente |

## Qué es

Un puñado corto de derivadas que se usan como piezas en todo lo demás: la constante, la
identidad, la potencia, el seno y el coseno, la exponencial y el logaritmo.

**No es una lista para memorizar sin más.** Cada una de ellas se dedujo de la definición o
de una regla anterior, y saber de dónde sale cada una es lo que permite reconstruirla
cuando se olvida.

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

- La tabla de básicas donde **cada fila se puede desplegar** y muestra su deducción, no
  solo su resultado.
- Cada función y su derivada **superpuestas**: se ve que donde la primera sube, la segunda
  es positiva.
- Un modo comparación entre $x^a$ y $a^x$ con un deslizador para $a$, para que la
  diferencia entre base y exponente sea visible y no una regla que se recuerda.
- Un ejercicio de cadena con la derivada interna **elegible de la tabla**, para que se vea
  qué pieza se está usando.

## Qué hay que entender antes

| Concepto previo | Por qué |
|---|---|
| `C-variable-de-derivacion` | Media lista deja de tener sentido si no está decidido respecto de qué se deriva: $a^x$ y $x^a$ se distinguen justo ahí |
| `C-pendiente-como-derivada` | Las básicas se deducen de la definición, que es una pendiente; sin eso la lista es arbitraria |
