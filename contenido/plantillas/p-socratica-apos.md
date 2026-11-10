# P-SOCRATICA-APOS · Andamiaje por transición de nivel

| | |
|---|---|
| **Identificador** | `P-SOCRATICA-APOS` |
| **Requisito** | `RC-PED-01` · prioridad **M** |
| **Transiciones** | Acción → Proceso · Proceso → Objeto |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué problema resuelve

El estudiante que falla no siempre falla en el mismo sitio, y **la pregunta que ayuda
depende de dónde esté**. `ADR-003` ya separa los tres registros por este motivo; APOS
separa los niveles por el mismo.

| Nivel | Qué puede hacer | Qué le falta |
|---|---|---|
| **Acción** | Ejecutar el procedimiento cuando se lo indican paso a paso | El procedimiento no es suyo: no lo puede describir sin hacerlo |
| **Proceso** | Describir el procedimiento entero sin ejecutarlo | Todavía no lo trata como una cosa sobre la que operar |
| **Objeto** | Tomar el procedimiento como objeto: componerlo, compararlo, aplicarle otro | — |

**La consecuencia práctica, y es la razón de esta plantilla:** dar una explicación de nivel
Objeto a quien está en Acción no enseña, abruma. Y repetir el procedimiento a quien ya está
en Proceso aburre y confirma que la clase no escucha.

## Acción → Proceso · cuatro turnos

<!-- repertorio: inicio -->

**Se usa cuando** el estudiante ejecuta bien y no puede decir qué ejecutó, o ejecuta mal y
al preguntarle por qué responde repitiendo los pasos.

| | Turno | Ranura |
|---|---|---|
| **1** | *«Antes de calcular nada: ¿qué te van a pedir que hagas primero?»* | — |
| **2** | *«Hiciste ‹PASO›. ¿Por qué ese y no otro?»* | `‹PASO›` = un paso que el estudiante escribió |
| **3** | *«Si te dieran ‹VARIANTE›, ¿cambiaría ese primer paso?»* | `‹VARIANTE›` = el mismo ejercicio con una pieza cambiada |
| **4** | *«Descríbeme el camino entero sin hacer las cuentas.»* | — |

**El turno 4 es el que marca la transición.** Si el estudiante lo responde, ya no está en
Acción: describir sin ejecutar *es* el nivel Proceso. Si no lo responde, se vuelve al 2 con
otro paso, y **no se pasa a Objeto**.

**Turno 3, el que hace el trabajo.** La variante no es un ejercicio nuevo: es el mismo con
una pieza cambiada, y la pregunta es si el primer paso resiste. Un procedimiento que solo
funciona para el caso que se practicó no se ha entendido, se ha memorizado.

<!-- repertorio: fin -->

## Proceso → Objeto · cuatro turnos

<!-- repertorio: inicio -->

**Se usa cuando** el estudiante describe el procedimiento entero con soltura y se atasca en
cuanto hay que aplicarle algo: componerlo con otro, compararlo con un caso, o usar el
resultado como entrada de lo siguiente.

| | Turno | Ranura |
|---|---|---|
| **1** | *«Sin calcularlo: ¿qué **clase** de cosa te va a salir?»* | — |
| **2** | *«¿Y si a eso que te sale le vuelves a aplicar lo mismo?»* | — |
| **3** | *«‹FORMA A› y ‹FORMA B› no se parecen. ¿Pueden ser la misma cosa?»* | `‹FORMA A›`, `‹FORMA B›` = dos escrituras del mismo objeto |
| **4** | *«¿Para qué te sirve saber que existe, si no lo puedes calcular?»* | — |

**El turno 1 separa los dos niveles mejor que ninguna otra pregunta.** *«¿Qué clase de
cosa?»* —un número, una función, una recta, una tasa con unidades— exige mirar el
procedimiento desde fuera. Quien está en Proceso responde contando los pasos.

**El turno 4 solo se usa con enunciados de existencia** —el teorema del valor medio, la
derivabilidad— y no se le pide a quien está en Acción: es la pregunta que convierte un
teorema en herramienta.

<!-- repertorio: fin -->

## Cómo se elige la transición

**Del nivel APOS que el fragmento recuperado declara**, no de una suposición sobre el
estudiante. Cada fragmento del corpus trae `nivel_apos` en su portada desde el incremento 1
—es uno de los tres metadatos que `RF-COR-01` exige—, así que el andamiaje se alinea con el
material que se va a citar y no con una etiqueta escrita aparte.

> Es la misma disciplina que `PM-C03` fijó para el vínculo concepto↔fragmento: **se deriva
> de lo que los dos lados ya traen, no se declara una segunda vez.**

## Lo que esta plantilla no hace

**No decide si hay que andamiar.** Eso lo decide el diagnóstico —`PM-B08`— y la compuerta
de contexto del filtro 4. Aquí solo está escrito qué preguntar una vez decidido.

**No enuncia el resultado en ningún turno.** Las ranuras admiten lo que el estudiante
escribió y variantes del enunciado; ninguna admite la respuesta. Ver el LEEME.

---

*Plantilla · `PM-C14` · `RC-PED-01` · IU Colegio Mayor del Cauca*
