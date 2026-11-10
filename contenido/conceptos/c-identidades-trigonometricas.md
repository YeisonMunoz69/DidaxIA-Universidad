# C-identidades-trigonometricas · Tres que hacen casi todo el trabajo

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-identidades-trigonometricas` |
| **Nodo del grafo** | `N14` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

Las identidades son igualdades que valen **para todo valor del ángulo**, no ecuaciones que
se resuelven. En este curso hacen dos trabajos concretos: permiten **deducir** las
derivadas del seno y del coseno, y permiten **reconocer** que dos resultados distintos son
el mismo.

Con tres basta para casi todo: la pitagórica, y las de ángulo doble del seno y del coseno.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Dar por incorrecta una derivada propia porque no coincide letra por letra con la del
  libro
- No poder seguir la deducción de $D_x(\sin x)$, que necesita la identidad de suma de
  ángulos
- Usar las identidades solo cuando el enunciado dice «simplifique», y no como herramienta
  de comprobación
- Tratar una identidad como una ecuación y ponerse a despejar el ángulo

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

*(Ninguna dentro del alcance del curso: vienen de la formación previa en trigonometría.)*

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

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- Dos expresiones trigonométricas y **sus dos gráficas superpuestas**: si son idénticas, se
  ve una sola curva.
- Un deslizador de ángulo que evalúa **las dos a la vez** y muestra los dos números, para
  que «coinciden en todos» se experimente y no se afirme.
- Un caso donde **no** coinciden, con dos curvas separadas, para que la herramienta no se
  lea como «siempre da igual».
- La identidad de suma de ángulos aplicada paso a paso dentro del cociente incremental del
  seno, con el nombre de lo que se usa en cada paso.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M10`
—equivalencia algebraica de resultados trigonométricos— lo declaraba como prerrequisito y
el banco no lo tenía.

El corpus lo cubre desde `PM-C07`: `F-036` deduce $D_x(\sin x)$ con la identidad de suma de
ángulos, y los fragmentos de `N14` de `PUR` y `PIS` la usan en cadena.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
