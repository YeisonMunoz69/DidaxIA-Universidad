# Plantillas socráticas y secuencias de remediación · `PM-C14`

> ⚠️ **Contenido, no código.** Como el banco de conceptos y el corpus, esto lo revisan y
> corrigen las docentes. No se genera por script. `DD-13`.

| | |
|---|---|
| **Qué es** | Lo que el generador usa **en lugar de dar la respuesta**: preguntas que llevan al estudiante a encontrarla |
| **Quién lo consume** | `PM-B05` —bloques verificables— y `PM-B06` —construcción del prompt— |
| **Qué requisito lo pide** | `RC-PED-01`, `-02`, `-06`, `-19` y `-20`, los cinco de prioridad **M** dentro del alcance v1 |

---

## Por qué esto vive aparte del banco de conceptos

**Porque tiene otro lector.** Una página de concepto la lee una docente y la corrige; una
plantilla la rellena el generador en tiempo de turno. Meter las dos cosas en el mismo
archivo obliga a quien revisa contenido a leer andamiaje de máquina, y a quien programa el
generador a leer prosa pedagógica para encontrar la ranura.

Están **enlazadas**, no separadas: cada concepción del banco tiene su secuencia aquí, y el
vínculo se comprueba —no se declara— en `../conceptos/verificar-conceptos.py`.

## Las dos clases de archivo

| Prefijo | Qué es | Cuántos |
|---|---|---|
| `p-…` | **Plantilla.** Reutilizable, con ranuras. No habla de ninguna concepción concreta | 5 |
| `s-…` | **Secuencia.** Una plantilla ya rellenada para **una** concepción del banco | 11 |

Una secuencia sin plantilla detrás sería contenido suelto; una plantilla sin ninguna
secuencia sería una promesa. Por eso el comprobador exige las dos direcciones.

## Qué cubre cada plantilla, y con qué criterio de aceptación

| Archivo | Requisito | Cómo se comprueba que está cumplido |
|---|---|---|
| [`p-socratica-apos.md`](p-socratica-apos.md) | `RC-PED-01` **M** | Hay secuencias de los niveles **Acción→Proceso** y **Proceso→Objeto** |
| [`p-scaffolding-kq1-kq5.md`](p-scaffolding-kq1-kq5.md) | `RC-PED-02` **M** | Los cinco pasos existen y están parametrizados por tipo de concepción |
| [`p-two-tier.md`](p-two-tier.md) | `RC-PED-06` **M** | Existe para el nodo de la regla de la cadena y sus razones cubren los cuatro estados |
| [`p-retroalimentacion-autoconcepto.md`](p-retroalimentacion-autoconcepto.md) | `RC-PED-19` **M** | **Al menos 10** variantes, y nombran la capacidad y no el resultado |
| [`p-autorregulacion.md`](p-autorregulacion.md) | `RC-PED-20` **M** | **Al menos 10** variantes de estrategia y de comprobación |

## Cómo se marca lo que el generador puede usar

**No todo lo que hay en un archivo es repertorio.** Estos documentos están
escritos para una docente que los revisa: traen tabla de metadatos, criterios de
aceptación, explicaciones y **anti-ejemplos** —lo que precisamente no hay que
decir—. El generador sólo puede recibir las preguntas y las variantes.

La frontera son dos marcas, y las dos hacen falta:

| Marca | Qué delimita |
|---|---|
| `<!-- repertorio: inicio -->` … `<!-- repertorio: fin -->` | **La región.** Todo lo que quede fuera no entra jamás, aunque esté en una tabla. Es un comentario de Markdown: no se ve al leer el documento renderizado |
| `*«…»*` | **La pieza.** Dentro de la región, sólo cuentan las citas en *cursiva*. Un anti-ejemplo citado en la misma fila va sin cursiva, y por eso no entra |

Y las citas en bloque se leen **enteras**: una pregunta partida en dos líneas
por el ancho del documento sigue siendo una pregunta.

> **Si un archivo no lleva las marcas, o le falta el cierre, no aporta ninguna
> pieza y el sistema lo declara** en `/api/salud`. No se cae a leer el archivo
> entero: contenido mal delimitado interpretado como repertorio válido es
> exactamente el defecto que estas marcas cierran.

**Qué produce hoy cada archivo** —el número está escrito en el propio documento
o se cuenta a mano en él, y una prueba lo comprueba archivo por archivo:

| Archivo | Piezas |
|---|---|
| `p-socratica-apos.md` | 8 · dos transiciones × cuatro turnos |
| `p-scaffolding-kq1-kq5.md` | 5 · los cinco pasos |
| `p-two-tier.md` | 15 · tres ítems × (enunciado + cuatro razones) |
| `p-retroalimentacion-autoconcepto.md` | 14 |
| `p-autorregulacion.md` | 14 |
| `s-…` | entre 5 y 10, según la secuencia |

## La regla que gobierna todas: **no se responde**

Una plantilla que en algún paso enuncia el resultado deja de ser andamiaje. `RC-PED-01` lo
dice por su nombre —*«en lugar de respuestas directas»*— y `R-22` lo vigila desde el otro
lado: el desarrollo precalculado **está en el contexto** y nada impide al modelo emitirlo.

> **Aquí eso se traduce en una prohibición concreta:** ninguna ranura de estas plantillas
> admite el resultado del ejercicio. Las ranuras son de **lo que el estudiante escribió** y
> de **lo que la concepción predice**, nunca de lo que hay que contestar.

## Qué NO está aquí, y por qué

**`RC-PED-03` no se puede escribir hoy.** Pide una plantilla de cuantificadores anidados
para la definición ε-δ, y su criterio de aceptación es *«la plantilla existe para el nodo
de límite formal»*. `N01` tiene **cero fragmentos por decisión escrita** —el alcance
declara límite y continuidad *«únicamente como prerrequisito declarativo»*—, de modo que la
plantilla nacería sin material que citar. **Es el mismo bloqueo que dejó a `M01` fuera del
mapa**, y la salida es la misma decisión, no más contenido.

**Las de prioridad `S` y `C` no entran en esta tanda:** `RC-PED-04`, `-05`, `-07` a `-09`,
`-11` a `-17`. No están descartadas; están fuera del alcance v1, que es lo que `PM-C14`
cubre. `RC-PED-18` la propia especificación la marca `W` y fuera del alcance.

> ### ⚠️ El pie de cada secuencia cita requisitos `S` que **no** están cumplidos
>
> Siete secuencias llevan en su pie un `RC-PED-` de prioridad `S` o `C` porque **tocan**
> lo que ese requisito pide, y conviene que la traza exista. **Tocar no es cumplir**, y la
> diferencia se declara aquí en vez de dejarla a interpretación:
>
> | Requisito | Qué pide | Qué hay hoy |
> |---|---|---|
> | `RC-PED-04` | Plantilla de razonamiento visual por contradicción $f \leftrightarrow f'$ | `S-M12` usa una contradicción visual **para un caso**. No es la plantilla |
> | `RC-PED-05` | Andamiaje del valor medio en comparación entre **dos** procesos | `S-M11` trabaja el enunciado de existencia, no el escenario de comparación |
> | `RC-PED-08` | Subpreguntas de interpretación física previas al procedimiento | `S-M14` las trae **completas**: contexto, unidad y condición inicial. Es lo más cerca de cumplido de las siete |
> | `RC-PED-09` | Actividad de traducción algebraico→gráfico de $f'$ **como función** | `S-M06` traduce en la dirección contraria y sobre $f$ |
> | `RC-PED-11` | **Dos pares** de ejemplos contrastantes Acción/Objeto por concepto | `S-M09` trae uno, y solo para un concepto |
> | `RC-PED-13` | Sondeo conceptual ante la generalización del conjugado | `S-M16` **lo cumple**: su `KQ3` es sondeo y no corrección procedimental |
> | `RC-PED-14` | **Colección** de pares simbólicamente similares y semánticamente distintos | `S-M10` usa un par. Una colección es otra cosa |
>
> **Los únicos que esta tanda da por cumplidos son los cinco `M` de la tabla de arriba,
> más `RC-PED-10` y `RC-PED-13`.** El resto son trazas para que quien retome el hilo sepa
> dónde hay algo empezado, no casillas que marcar.

**`RC-PED-10` no necesita archivo propio.** Pide contenido de remediación diferenciado por
cada concepción del catálogo dentro del alcance, y eso ya existe: cada `s-…` de esta
carpeta es la remediación de **una** concepción y de ninguna otra. El comprobador lo cuenta.

## Lo que falta, y no se disimula

**Ninguna de estas plantillas está revisada por una docente.** Se escribieron el
2026-08-10, después de la sesión del 09 —que además fue **sin lectura a fondo**—, así que
ni siquiera están cubiertas por aquel *«no señalaron correcciones»*. Van en `PM-X01` con
las 18 páginas de concepto.

**Y no están medidas.** Que una secuencia lleve al estudiante donde pretende es una
afirmación empírica, y este proyecto tiene un sitio para eso: las mediciones de la familia
B, `PM-V05`. Hasta entonces son contenido razonado, no contenido validado.

---

*Plantillas · `PM-C14` · `DD-13` · IU Colegio Mayor del Cauca*
