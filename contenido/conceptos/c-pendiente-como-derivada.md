# C-pendiente-como-derivada · La pendiente necesita dos puntos

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-pendiente-como-derivada` |
| **Nodo del grafo** | `N06` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

La pendiente de una recta es $\frac{\Delta y}{\Delta x}$: **cuánto sube por cada unidad que
avanza**. Es un cociente, y un cociente necesita dos puntos.

De ahí sale todo lo demás. La derivada en un punto es una pendiente, y por eso su
definición tiene que fabricar un segundo punto —el $x+h$— y después acercarlo.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Buscar «la pendiente en un punto» sin ver que hace falta algo más que ese punto
- Confundir el **valor** de la función con su **inclinación**: creer que donde la curva
  está alta la derivada es grande
- No leer el signo: no asociar pendiente negativa con función que decrece
- Tratar la fórmula $\frac{f(x+h)-f(x)}{h}$ como algo que hay que memorizar, y no como la
  pendiente de siempre entre dos puntos de la curva

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

| Concepto previo | Por qué |
|---|---|
| `C-razon-y-proporcion` | La pendiente **es** una razón entre dos variaciones; sin manejar el cociente como objeto no hay pendiente |

## La explicación

Conviene enseñarla con las unidades puestas, porque las unidades hacen visible que es un
cociente: si el eje horizontal son segundos y el vertical metros, **la pendiente se mide en
metros por segundo**. La barra no es adorno.

Y el paso a la derivada se cuenta en una frase: *la recta entre dos puntos de la curva
tiene pendiente; acerca el segundo al primero y esa pendiente se acerca a un número; ese
número es la derivada*. Nada nuevo salvo el paso al límite.

**Alto no es lo mismo que empinado**, y merece decirse aparte porque es el error de lectura
más común en una gráfica: el valor de $f$ y el valor de $f'$ son dos cosas que se leen en
sitios distintos del dibujo.

## Qué muestra la simulación

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- Una recta con **dos puntos arrastrables** y su $\Delta y$ y $\Delta x$ dibujados como
  catetos, con el cociente calculado en pantalla.
- Al mover los puntos sobre la misma recta, **el cociente no cambia**: es lo que hace que
  la pendiente sea de la recta y no de los puntos.
- Sobre una curva, un punto alto con pendiente pequeña y un punto bajo con pendiente
  grande, señalados a la vez, contra la confusión entre alto y empinado.
- El signo de la pendiente y el sentido de la curva, resaltados juntos.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M22`
lo declaraba como prerrequisito y el banco no lo tenía.

Sostiene además a `C-M18` —«tiende a» frente a «llega a»—: la objeción de que los dos
puntos no pueden juntarse solo tiene fuerza si antes está claro que **hacen falta dos**.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
