# C-identidades-trigonometricas · Tres que hacen casi todo el trabajo

| | |
|---|---|
| **Identificador** | `C-identidades-trigonometricas` |
| **Nodo del grafo** | `N14` |
| **Concepción errónea asociada** | `— · **no es una concepción errónea, es un prerrequisito**` |
| **Estado** | Borrador · pendiente de revisión docente |

## Qué es

Las identidades son igualdades que valen **para todo valor del ángulo**, no ecuaciones que
se resuelven. En este curso hacen dos trabajos concretos: permiten **deducir** las
derivadas del seno y del coseno, y permiten **reconocer** que dos resultados distintos son
el mismo.

Con tres basta para casi todo: la pitagórica, y las de ángulo doble del seno y del coseno.

## La explicación

La diferencia entre identidad y ecuación es la primera frase y no es un tecnicismo: **una
identidad es cierta para todos los valores; una ecuación, para algunos**. Comprobar una
identidad en dos o tres valores no la demuestra, pero **desmentirla basta con uno**, y esa
asimetría es utilísima en la práctica.

De ahí sale la comprobación que conviene enseñar antes que ninguna manipulación: ante dos
expresiones que deberían ser iguales, **evaluarlas en un par de números**. Si difieren, hay
error; si coinciden, merece la pena buscar la identidad que las une.

Y la de suma de ángulos merece mención aparte porque es la que **hace posible** derivar el
seno: el cociente incremental necesita desarrollar $\sin(x+h)$, y sin esa identidad no hay
por dónde empezar. No es un requisito administrativo — es la pieza que abre el cálculo.

## Qué muestra la simulación

- Dos expresiones trigonométricas y **sus dos gráficas superpuestas**: si son idénticas, se
  ve una sola curva.
- Un deslizador de ángulo que evalúa **las dos a la vez** y muestra los dos números, para
  que «coinciden en todos» se experimente y no se afirme.
- Un caso donde **no** coinciden, con dos curvas separadas, para que la herramienta no se
  lea como «siempre da igual».
- La identidad de suma de ángulos aplicada paso a paso dentro del cociente incremental del
  seno, con el nombre de lo que se usa en cada paso.
