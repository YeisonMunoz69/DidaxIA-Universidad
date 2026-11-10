# C-variable-de-derivacion · Respecto de qué se deriva

| | |
|---|---|
| **Identificador** | `C-variable-de-derivacion` |
| **Nodo del grafo** | `N05` |
| **Concepción errónea asociada** | `— · **no es una concepción errónea, es un prerrequisito**` |
| **Estado** | Borrador · pendiente de revisión docente |

## Qué es

Derivar no es una operación sobre una expresión: es una operación **sobre una expresión
respecto de una variable**. En $f(x) = a x^2$ hay dos letras, y solo una de ellas varía.
La otra es una constante escrita con letra.

**Sin decidir eso, la derivada no está definida** — y el estudiante que no lo decide
deriva todas las letras por igual.

## La explicación

La notación lo dice y casi nadie la lee: $\frac{df}{dx}$ **lleva la variable escrita
abajo**. La prima de $f'(x)$ la esconde, y por eso es cómoda y por eso confunde.

La pregunta que ordena todo: *si la $a$ cambiara, ¿estaríamos hablando de la misma
función?* Si la respuesta es no —si al cambiar $a$ tenemos otra función distinta—, entonces
$a$ es un parámetro y no se deriva.

Y conviene decir que **la misma letra puede ser variable en un problema y constante en
otro**. No hay letras que sean «de constante»: hay un papel que se les asigna, y ese
papel es parte del enunciado, no de la letra.

## Qué muestra la simulación

- La misma expresión $a x^2$ con **dos deslizadores**: uno para $x$ y otro para $a$. Al
  mover $x$ se recorre una curva; al mover $a$ **se cambia de curva**, y la familia entera
  se ve como un haz.
- Un interruptor «derivar respecto de $x$ / respecto de $a$» que muestra **dos resultados
  distintos para la misma expresión**.
- La notación $\frac{df}{dx}$ y $\frac{df}{da}$ escritas junto a cada resultado, para que
  la variable esté siempre a la vista.

## Qué hay que entender antes

| Concepto previo | Por qué |
|---|---|
| `C-razon-y-proporcion` | La derivada es un cociente de variaciones, y solo varía lo que se ha declarado variable |
