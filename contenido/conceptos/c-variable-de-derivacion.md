# C-variable-de-derivacion · Respecto de qué se deriva

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-variable-de-derivacion` |
| **Nodo del grafo** | `N05` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

Derivar no es una operación sobre una expresión: es una operación **sobre una expresión
respecto de una variable**. En $f(x) = a x^2$ hay dos letras, y solo una de ellas varía.
La otra es una constante escrita con letra.

**Sin decidir eso, la derivada no está definida** — y el estudiante que no lo decide
deriva todas las letras por igual.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Derivar la $a$ de $a x^2$ «porque es una letra»
- Derivar $\pi$ cuando aparece en la función
- Creer que la derivada de $y = c$, con $c$ una letra, no puede ser cero
- Al derivar $kx$ respecto de $x$, escribir $1$ porque «la $k$ desaparece»
- En un problema de razones relacionadas, no distinguir qué depende del tiempo y qué no

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

| Concepto previo | Por qué |
|---|---|
| `C-razon-y-proporcion` | La derivada es un cociente de variaciones, y solo varía lo que se ha declarado variable |

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

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- La misma expresión $a x^2$ con **dos deslizadores**: uno para $x$ y otro para $a$. Al
  mover $x$ se recorre una curva; al mover $a$ **se cambia de curva**, y la familia entera
  se ve como un haz.
- Un interruptor «derivar respecto de $x$ / respecto de $a$» que muestra **dos resultados
  distintos para la misma expresión**.
- La notación $\frac{df}{dx}$ y $\frac{df}{da}$ escritas junto a cada resultado, para que
  la variable esté siempre a la vista.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M23`
—constante simbólica frente a variable— lo declaraba como prerrequisito y el banco no lo
tenía.

Está muy cerca de `M23`, y la frontera conviene tenerla escrita: **`M23` es el error;
esto es la habilidad que lo evita**. Por eso este archivo no lleva concepción asociada.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
