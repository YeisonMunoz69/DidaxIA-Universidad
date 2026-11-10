# C-diferencia-de-potencias · El conjugado es un caso de una familia

| | |
|---|---|
| **Identificador** | `C-diferencia-de-potencias` |
| **Nodo del grafo** | `N13` |
| **Concepción errónea asociada** | `— · **no es una concepción errónea, es un prerrequisito**` |
| **Estado** | Borrador · pendiente de revisión docente |

## Qué es

La factorización $a^n - b^n = (a-b)(a^{n-1} + a^{n-2}b + \dots + b^{n-1})$, de la que
**todo el mundo conoce solo el caso $n=2$** con el nombre de «diferencia de cuadrados».

Es el prerrequisito que convierte el conjugado de un truco en una elección: **el índice de
la raíz decide cuántos sumandos lleva el segundo factor**.

## La explicación

Conviene verla al revés de como se suele enseñar: **no son fórmulas distintas, es una sola
con un parámetro**. El segundo factor tiene exactamente $n$ sumandos, y en cada uno el
exponente de $a$ baja mientras el de $b$ sube.

| $n$ | Factorización |
|:--:|---|
| 2 | $(a-b)(a+b)$ |
| 3 | $(a-b)(a^2 + ab + b^2)$ |
| 4 | $(a-b)(a^3 + a^2b + ab^2 + b^3)$ |

Y la comprobación de que funciona es un minuto de distributiva: al multiplicar, **todo se
cancela en cascada** y sobreviven solo $a^n$ y $-b^n$. Verlo cancelar una vez vale más que
memorizar las tres filas.

**Para qué sirve en este curso:** para derivar $\sqrt[n]{x}$ por definición. El cociente
incremental tiene una resta de raíces arriba, y multiplicar por el factor que le
corresponde a su índice es lo que la convierte en una resta sin raíces.

## Qué muestra la simulación

- Un deslizador de $n$ que **reescribe el segundo factor** y hace visible cómo crece el
  número de sumandos.
- La multiplicación desarrollada con los términos intermedios **tachándose en cascada**,
  para que la cancelación se vea ocurrir.
- El caso $n=2$ marcado como uno más de la familia, no como la regla.
- Un cociente incremental con raíz de índice elegible, y el factor correcto ofrecido junto
  a otro incorrecto, para elegir.
