# P-TWO-TIER · Turno de cálculo y turno de razón

| | |
|---|---|
| **Identificador** | `P-TWO-TIER` |
| **Requisito** | `RC-PED-06` · prioridad **M** · sostiene `RF-DGC-01` |
| **Nodo obligatorio** | `N08` · regla de la cadena |
| **Nodos con ítem escrito** | `N08` · `N14` · `N05` — las tres familias que `RC-PED-06` nombra |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Por qué dos turnos y no uno

**Porque una respuesta correcta no prueba comprensión y una incorrecta no prueba su
ausencia.** El formato de dos niveles separa las dos cosas preguntando primero el resultado
y después la razón, y esa separación es lo que produce un estado diagnóstico en vez de una
nota.

Es además el mecanismo que `R-09` obliga a tener: **ninguna de las taxonomías de
concepciones se validó en diálogo espontáneo**, todas vienen de exámenes y encuestas. El
ítem estructurado es la vía de detección que no depende de que el estudiante enuncie su
error en texto libre.

## Los cuatro estados

|  | **Razón correcta** | **Razón incorrecta** |
|---|---|---|
| **Respuesta correcta** | `E1` · **comprensión** | `E2` · **acierto sin comprensión** |
| **Respuesta incorrecta** | `E3` · **error de ejecución** | `E4` · **concepción errónea** |

**`E2` es el estado que justifica todo el formato.** Sin el segundo turno se registra como
acierto, el sistema avanza de tema y la concepción sigue ahí — intacta y ahora invisible.
Con el segundo turno se distingue, y es el único de los cuatro que un ítem de un solo nivel
no puede ver.

**`E3` y `E4` se atienden distinto, y confundirlos es caro.** A `E3` le sobra explicación:
sabe lo que hace y se equivocó al hacerlo. A `E4` le sobra práctica: repetir ejercicios
consolida la regla equivocada.

| Estado | Qué sigue |
|---|---|
| `E1` | Se avanza. No se explica lo que ya se entendió |
| `E2` | `P-KQ1-KQ5` desde `KQ2` — hay que hacer explícita la regla que usó |
| `E3` | Se señala el paso y se sigue. No hay concepción que remediar |
| `E4` | La secuencia `s-…` de la concepción que la razón elegida delata |

## Los tres ítems

`RC-PED-06` pide el formato para **compuestas**, **trigonométricas** y **constantes
simbólicas**. El esqueleto no cambia; cambian el ejercicio y las cuatro razones.

| Familia | Nodo | Ítem | Concepciones que delatan las razones |
|---|---|---|---|
| Compuestas | `N08` | $y = \cos^3 x$ | `M21` · `M22` |
| Trigonométricas | `N14` | $y = \sin x \cos x$ | `M22` · `M10` — dos formas correctas que no se parecen |
| Constantes simbólicas | `N05` | $y = a x^2 + k$ | `M23` — la letra que no es variable |

**Las opciones no se barajan al azar entre concepciones.** Una razón que no delata nada
convierte el ítem en adivinanza y estropea el estado: la parrilla de arriba solo funciona
si «razón incorrecta» significa **una** concepción identificable.

**Y las concepciones que se delatan son de las que tienen secuencia escrita** —`s-m21.md`,
`s-m22.md`, `s-m10.md`, `s-m23.md`—. No es un detalle de inventario: `E4` manda a *«la
secuencia de la concepción que la razón elegida delata»*, así que delatar una que no la
tiene dejaría al estudiante diagnosticado y sin remediación, que es peor que no
diagnosticarlo.

**Cada ítem declara su expresión también en notación corriente, y no es redundancia.** Esa
fila dice lo mismo que el enunciado en LaTeX, y está por un motivo concreto: el LaTeX está
escrito para la docente que revisa este archivo (`DD-13`) y **el motor simbólico lee la otra
notación**, así que hasta hoy alguien traducía de una a otra por el camino. Traducir es
adivinar en cuanto la escritura cambia, y equivocarse ahí corrige el turno 1 **contra otro
ejercicio**: el estado saldría al revés sin que nada fallara. Escribirlo dos veces cuesta
una línea y quita la adivinanza. Si las dos formas dejaran de coincidir lo dice una prueba,
que deriva la declarada con el motor de verdad.

*(Nota de forma, para quien edite esto: las líneas que empiezan por `|` o por `>` son las
que el cargador toma como repertorio para el generador. Una explicación como ésta va en
prosa corrida a propósito — en cita en bloque acabaría dentro del prompt.)*

### `N08` · funciones compuestas

<!-- repertorio: inicio -->

| | |
|---|---|
| **Nodo** | `N08` |
| **Expresión, en notación corriente** | `cos(x)^3` |
| **Concepciones que delatan las razones** | `M21` · `M22` |

**Turno 1 · cálculo.** Se pide el resultado y nada más.

> *«Deriva $y = \cos^3 x$. Escribe solo el resultado.»*

**Turno 2 · razón.** Se ofrecen cuatro opciones, y **cada una está escrita para delatar una
concepción concreta**, no para ser plausible en general.

| | Opción de razón | Qué delata |
|---|---|---|
| **a** | *«Derivé la potencia y multipliqué por la derivada de lo de dentro.»* | Razón correcta |
| **b** | *«Derivé la potencia; lo de dentro es coseno y ya está derivado.»* | `M21` · no ve la composición |
| **c** | *«Derivé la potencia y multipliqué por $\sin x$.»* | `M22` · el signo del coseno |
| **d** | *«Es $\cos^3 x$, así que derivé el exponente.»* | Confusión de $\cos^3 x$ con $\cos(x^3)$ · `M21` en su otra forma |

<!-- repertorio: fin -->

### `N14` · derivadas de funciones trigonométricas

<!-- repertorio: inicio -->

| | |
|---|---|
| **Nodo** | `N14` |
| **Expresión, en notación corriente** | `sen(x)*cos(x)` |
| **Concepciones que delatan las razones** | `M22` · `M10` |

**Turno 1 · cálculo.**

> *«Deriva $y = \sin x \cos x$. Escribe solo el resultado.»*

**Turno 2 · razón.**

| | Opción de razón | Qué delata |
|---|---|---|
| **a** | *«Usé la regla del producto: la derivada del seno por el coseno, más el seno por la derivada del coseno, que es -sen(x).»* | Razón correcta |
| **b** | *«Usé la regla del producto, y como la derivada de cos(x) es sen(x), los dos sumandos me quedaron positivos.»* | `M22` · el signo del coseno |
| **c** | *«Me salió cos(x)^2 - sen(x)^2, pero en el libro aparece cos(2x); como no se parecen, la mía tiene que estar mal.»* | `M10` · no reconoce la equivalencia |
| **d** | *«Usé la regla del producto y el signo menos lo puse en la derivada del seno, no en la del coseno.»* | `M22` en su otra forma · el signo existe, pero en el paso equivocado |

**Por qué la razón `c` no habla de derivar.** Es la única de las cuatro que describe lo que
el estudiante hizo **después** de derivar bien, y ahí está su valor: `M10` no es un fallo de
derivación sino de reconocimiento —`c-m10.md`: *«no falla la derivación, falla el
reconocimiento de equivalencia algebraica»*—. Quien la elige suele haber escrito la
respuesta correcta y haberla descartado, que es exactamente el `E2` de la parrilla y el
estado que este formato existe para ver.

<!-- repertorio: fin -->

### `N05` · constantes simbólicas

<!-- repertorio: inicio -->

| | |
|---|---|
| **Nodo** | `N05` |
| **Expresión, en notación corriente** | `a*x^2 + k` |
| **Concepciones que delatan las razones** | `M23` |

**Turno 1 · cálculo.**

> *«Deriva $y = a x^2 + k$ respecto de $x$. Escribe solo el resultado.»*

**Turno 2 · razón.**

| | Opción de razón | Qué delata |
|---|---|---|
| **a** | *«a y k no cambian cuando cambia x: la a se conserva como factor y la derivada de k es 0.»* | Razón correcta |
| **b** | *«a es una letra igual que x, así que la derivé también.»* | `M23` · la letra que se toma por variable |
| **c** | *«La derivada de k no puede ser 0, porque k es una letra y no un número.»* | `M23` en su segunda forma · la constante simbólica sin derivada nula |
| **d** | *«Las constantes se van al derivar, así que la a también se va y queda 2x.»* | `M23` en su tercera forma · la regla del múltiplo constante confundida con la de la constante |

**Aquí las tres razones incorrectas delatan la misma concepción, y es deliberado.** El
catálogo absorbió `M05` —rigidez simbólica ante constantes y parámetros— **dentro de
`M23`** (`MAPA-M01-M24.md`), así que en esta familia no hay una segunda concepción
comprometida que ofrecer: fabricarla para tener variedad sería inventar contenido. Lo que
sí cambia entre las tres es **la forma**, y las tres están tomadas de «Cómo se manifiesta»
de `c-m23.md`. Para la parrilla las tres significan lo mismo —`E4` con `s-m23.md`— y para
la docente que revise dicen por dónde entró el error.

**El enunciado dice «respecto de $x$» y los otros dos no.** Es la pregunta que `c-m23.md`
señala como la que resuelve la confusión —*«¿este símbolo cambia cuando cambia x?»*— y sin
ella el ítem sería ambiguo de verdad: con dos letras y ninguna variable declarada, derivar
respecto de `a` es una lectura legítima. Un ítem ambiguo no mide la concepción, mide la
suposición.

<!-- repertorio: fin -->

## Cuándo se activa, y cuándo no

**Preferentemente en ítems de nivel de aplicación**, que es donde `RF-DGC-02` sitúa la
evidencia sólida. En ítems de comprensión el efecto medido no es significativo, así que
usarlo ahí gasta un turno del estudiante sin ganar diagnóstico.

**No se activa dos veces seguidas.** Un formato de opción múltiple repetido deja de medir
razones y empieza a medir paciencia.

## Lo que esta plantilla no hace

**No clasifica.** Produce el par respuesta+razón; convertirlo en estado es `PM-B08`, el
diagnóstico conceptual de dos niveles, que es código y no contenido. Aquí está escrito qué
se pregunta y qué delata cada opción — que es exactamente lo que ese subsistema necesita
tener escrito antes de existir.

---

*Plantilla · `PM-C14` · `RC-PED-06` · IU Colegio Mayor del Cauca*
