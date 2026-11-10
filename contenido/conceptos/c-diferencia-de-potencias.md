# C-diferencia-de-potencias · El conjugado es un caso de una familia

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-diferencia-de-potencias` |
| **Nodo del grafo** | `N13` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

La factorización $a^n - b^n = (a-b)(a^{n-1} + a^{n-2}b + \dots + b^{n-1})$, de la que
**todo el mundo conoce solo el caso $n=2$** con el nombre de «diferencia de cuadrados».

Es el prerrequisito que convierte el conjugado de un truco en una elección: **el índice de
la raíz decide cuántos sumandos lleva el segundo factor**.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Multiplicar por $(a+b)$ ante una raíz cúbica y esperar que las raíces desaparezcan
- Conocer la diferencia de cuadrados y no reconocer $a^3 - b^3$ como lo mismo con otro $n$
- Memorizar por separado «diferencia de cuadrados» y «diferencia de cubos», sin ver que
  son dos filas de una tabla
- Concluir que un límite no existe porque el único factor conocido no cerró la
  simplificación

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

*(Ninguna dentro del alcance del curso: es álgebra previa.)*

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

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- Un deslizador de $n$ que **reescribe el segundo factor** y hace visible cómo crece el
  número de sumandos.
- La multiplicación desarrollada con los términos intermedios **tachándose en cascada**,
  para que la cancelación se vea ocurrir.
- El caso $n=2$ marcado como uno más de la familia, no como la regla.
- Un cociente incremental con raíz de índice elegible, y el factor correcto ofrecido junto
  a otro incorrecto, para elegir.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M16`
—la comprometida del conjugado— lo declaraba como prerrequisito y el banco no lo tenía.

Es la pieza que explica **por qué** la sobregeneralización de `M16` falla: no es que el
estudiante use mal el conjugado, es que solo conoce una fila de la tabla.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
