# P-KQ1-KQ5 · Andamiaje reflexivo de cinco pasos

| | |
|---|---|
| **Identificador** | `P-KQ1-KQ5` |
| **Requisito** | `RC-PED-02` · prioridad **M** |
| **Parametrizada por** | Tipo de concepción errónea |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Los cinco pasos

<!-- repertorio: inicio -->

**El orden importa y no se salta ninguno.** Cada paso solo funciona si el anterior se
cumplió: pedir revisión a quien no ha justificado su respuesta produce que la cambie por
obediencia, no por convicción — y eso deja la concepción intacta bajo una respuesta
correcta, que es el peor resultado posible.

| | Paso | Qué se dice | Qué se busca |
|---|---|---|---|
| **KQ1** | **Señalar** | *«Mira esta parte: ‹TROZO›.»* | Que el estudiante vuelva a un punto concreto, no a «revisa el ejercicio» |
| **KQ2** | **Justificar** | *«¿Por qué ahí va eso?»* | Hacer explícita la regla que **él** estaba usando |
| **KQ3** | **Contrastar** | *«¿Y en ‹CASO›? ¿Sigue valiendo lo que acabas de decir?»* | Que la regla choque con un caso donde no se sostiene |
| **KQ4** | **Revisar** | *«Con eso en la mano, ¿qué harías distinto?»* | Que la corrección salga de él |
| **KQ5** | **Confirmar** | *«Dime la regla como la dirías ahora.»* | Que la reconstrucción quede dicha, no supuesta |

**`KQ3` es el paso caro y el que no se puede improvisar.** El caso de contraste tiene que
ser uno en el que la regla equivocada **falla de forma visible** y la correcta no. Por eso
esta plantilla se parametriza: el contraste sale de la concepción, no del ejercicio.

<!-- repertorio: fin -->

## Cómo se parametriza · por tipo de concepción

| Tipo | Qué es | Qué sirve como `‹CASO›` de `KQ3` |
|---|---|---|
| **De alcance** | Una técnica válida aplicada donde no vale | El caso vecino donde la técnica **no cierra** — `M16`, `M21` |
| **De signo o de detalle** | El procedimiento es correcto y una pieza no | El caso donde ese detalle **cambia el resultado de forma comprobable** — `M22` |
| **De estatuto del símbolo** | Se confunde qué papel juega una letra | El mismo ejercicio con la letra sustituida por un número — `M23`, `M14` |
| **De representación** | Se trata una escritura como si fuera la cosa | La **otra** representación de la misma cosa — `M06`, `M10` |
| **De lectura de enunciado** | El cálculo está bien y la conclusión no se sostiene | El enunciado literal, leído despacio — `M11`, `M18` |
| **De confusión entre niveles** | Se mezclan dos objetos parecidos | Los dos objetos puestos uno al lado del otro — `M09`, `M12` |

> **El tipo no es un campo nuevo que haya que anotar en ninguna parte.** Sale de leer
> «Cómo se manifiesta» en la página del concepto, que es donde está escrito qué escribe el
> estudiante cuando tiene esa confusión. Cada secuencia `s-…` de esta carpeta declara el
> suyo, y el comprobador exige que sea uno de los seis.

## Dónde se corta

**`KQ4` y `KQ5` no se fuerzan.** Si en `KQ3` el estudiante sostiene su regla, la secuencia
**termina ahí** y el turno pasa a explicación directa con el fragmento del corpus que
corresponda. Insistir con un cuarto «¿y ahora?» convierte el andamiaje en interrogatorio, y
`ADR-006` ya decidió que más vale sin contexto que con contexto irrelevante — aquí el
principio es el mismo: más vale explicar que fingir un descubrimiento.

**`KQ1` no se usa si el estudiante no ha escrito nada.** Sin trozo que señalar no hay
andamiaje reflexivo: eso es `P-SOCRATICA-APOS`, que empieza antes de calcular.

## Lo que esta plantilla no hace

**No corrige.** En ninguno de los cinco pasos se dice qué es lo correcto. `KQ5` pide la
regla **al estudiante**; si la que dice sigue siendo la equivocada, el paso no se ha
cumplido y la secuencia termina como termina `KQ3`.

---

*Plantilla · `PM-C14` · `RC-PED-02` · IU Colegio Mayor del Cauca*
