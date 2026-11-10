# C-razon-y-proporcion · El cociente como objeto

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-razon-y-proporcion` |
| **Nodo del grafo** | `N07` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

Una razón es un cociente entre dos cantidades que se lee como **una sola magnitud nueva**:
km por hora, pesos por kilo, metros por segundo. No es una división pendiente de hacer: es
un objeto con su propio significado y sus propias unidades.

Todo el cálculo diferencial descansa aquí. Pendiente, tasa de cambio y derivada son la
misma razón vista de tres maneras.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- Dar la respuesta con las unidades de la magnitud y no las del cociente: «3 cm» donde va
  «3 cm/min»
- Sumar tasas como si fueran cantidades
- No poder invertir la razón cuando el problema lo pide —de cm/min a min/cm—
- Leer $\frac{\Delta y}{\Delta x}$ como «un $\Delta y$ y un $\Delta x$» y no como un número

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

*(Ninguna dentro del alcance del curso: es el prerrequisito más básico de la cadena y viene
de la formación previa.)*

## La explicación

Las unidades son el instrumento, y conviene no soltarlas nunca: **la barra del cociente se
lee «por»**. En cuanto se lee en voz alta —«tres centímetros **por** minuto»— la confusión
con «tres centímetros» se deshace sola.

La segunda idea es que **una razón puede crecer mientras la cantidad decrece, y al revés**.
Un depósito que se vacía cada vez más despacio tiene altura que baja y tasa que sube hacia
cero. Son dos números independientes y hay que mirarlos por separado.

Y la tercera, que es la que enlaza con el curso: **la razón entre dos variaciones es una
pendiente**. Si se dibujan las dos magnitudes en unos ejes, la razón es la inclinación de
la recta que une los dos estados. De ahí a la derivada solo falta acercarlos.

## Qué muestra la simulación

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- Dos magnitudes con sus unidades y **el cociente calculado con su unidad compuesta**, que
  cambia si se cambia cualquiera de las dos.
- Un depósito que se vacía con **dos lecturas simultáneas** —cantidad y tasa— que pueden
  moverse en sentidos opuestos.
- La misma razón dibujada como **inclinación** de un segmento en unos ejes, para que
  cociente y pendiente sean visiblemente lo mismo.
- Un botón de invertir la razón que da la vuelta a las unidades.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo. Existe porque `C-M14`
—tasa frente a cantidad— lo declaraba como prerrequisito y el banco no lo tenía, y porque
`C-M18` y `C-pendiente-como-derivada` se apoyan en él.

Es anterior al curso: pertenece a la formación previa, y por eso su página existe para
**diagnosticar**, no para enseñarlo por primera vez.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
