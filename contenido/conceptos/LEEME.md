# Banco de conceptos

> ⚠️ **Antes de modificar nada, lea [`../../../../ANTES-DE-MODIFICAR.md`](../../../../ANTES-DE-MODIFICAR.md).**

| | |
|---|---|
| **Qué es** | Los conceptos de cálculo diferencial que el sistema puede citar y explicar |
| **Decisión que lo crea** | [`DD-13`](../../../04-Decisiones-de-Detalle.md) |
| **Origen** | La consulta a las dos docentes del 2026-08-05 · [`09-Aportes`](../../../09-Aportes-de-la-Consulta-Docente.md) §3.2 |
| **Estado** | 🟡 **Tres conceptos en borrador, sin revisión docente** |

---

## Esto es contenido, no código

**Se edita a mano y no se genera.** Las docentes lo revisan, lo corrigen y lo amplían sin
que nadie tenga que desplegar nada. Esa es la razón entera de que `DD-13` lo colocara aquí
y no dentro de la aplicación.

Si mañana estos archivos se convirtieran en componentes, las docentes quedarían fuera de su
propia contribución.

---

## Qué concepciones reciben página

El catálogo de la revisión tiene **24 concepciones**, `M01`–`M24`, y el banco no tendrá 24
páginas. [`MAPA-M01-M24.md`](MAPA-M01-M24.md) decide cuáles sí y con qué motivo: **16
reciben página**, una se absorbe en otra y siete no, porque dos no son conceptos sino
creencias o conductas, cuatro caen fuera del programa del curso y una está excluida del
alcance por decisión escrita.

El orden lo fija el microcurrículo de Cálculo Diferencial de la institución.

---

## Los tres primeros, y por qué estos tres

`DD-13` fija que **se empieza por tres** y se mide cuánto cuesta uno antes de comprometer
el resto. Los elegidos no son arbitrarios:

| Archivo | Concepción | Por qué está |
|---|---|---|
| [`c-m21.md`](c-m21.md) | Reconocer la composición | Frecuencia **alta** en el catálogo, la mayor de las cuatro comprometidas. **Las dos docentes la marcaron «Mucha»** |
| [`c-m22.md`](c-m22.md) | El signo de la derivada del coseno | Desbloquea las diagnósticas Q68, Q69 y Q70 |
| [`c-m23.md`](c-m23.md) | Constante simbólica frente a variable | Desbloquea Q71, Q72, Q73 y Q74 |

**Los dos últimos existen por una razón concreta y medible.** El criterio pre-registrado de
`E02` tiene una condición abierta: el grafo no cubre las cuatro concepciones comprometidas,
y por eso **siete preguntas diagnósticas puntuarían bajo por ausencia de arista y no por
fallo del modelo**. Estos archivos son esa cobertura.

---

## Qué lleva cada concepto

**Las aristas de prerrequisito son la parte que más importa.** Al escribir «para entender
esto hace falta antes aquello», se está dibujando el grafo pedagógico. Que las docentes lo
hagan en prosa y no en un editor de grafos es deliberado.

| Sección | Para qué |
|---|---|
| Qué es | La definición, en una frase |
| Cómo se manifiesta | **Lo que el estudiante escribe** cuando tiene la confusión. Es lo que la detección usa |
| Qué hay que entender antes | **Las aristas del grafo**, con su motivo |
| La explicación | Lo que el sistema puede citar |
| Qué muestra la simulación | **Qué ocurre al mover los parámetros**, no qué se dibuja |
| Procedencia | De qué concepción del catálogo sale y a qué preguntas respalda |

> **La simulación se describe, no se programa aquí.** `Simulacion.svelte` es un intérprete:
> lee esta sección y la representa. Si cada concepto trajera su propio componente, el banco
> volvería a ser código.

---

## Lo que falta, y no se disimula

**Ninguno de los tres está revisado por una docente.** Están escritos desde el catálogo de
la revisión sistemática y desde las respuestas de la consulta, que es un origen razonable y
no es lo mismo que la validación de quien enseña.

Cada archivo lleva su lista de pendientes al final. Los tres comparten los mismos:

- Revisión de una docente de cálculo
- Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- Comprobación matemática al ingerir, según `DD-02`

**No se dan por buenos hasta entonces.** El estado dice «borrador» en la cabecera de cada
uno precisamente para que nadie los cite como si estuvieran cerrados.

---

## Comprobar el banco

```bash
# desde la raíz del repositorio
python OE3-Implementacion/codigo/contenido/conceptos/verificar-conceptos.py
```

Comprueba que cada concepto tenga sus secciones, que las aristas apunten a conceptos que
existen o estén declaradas como pendientes, **qué fragmentos del corpus ilustran cada
concepto** y **qué preguntas diagnósticas quedan sin cubrir**. Esa última cifra es la que
cierra la condición 5 de `E02`.

### El vínculo con el corpus no se escribe en ninguna parte · `PM-C03`

**Se deriva**, de dos claves que los dos lados ya traen: la concepción asociada del
fragmento y su nodo del grafo. Declararlo además —una lista de fragmentos dentro del
concepto, o un campo `concepto:` en el fragmento— sería una segunda clasificación que
puede desincronizarse de la primera, y `DD-15` exige poder **retirar** fragmentos, con lo
que esa lista quedaría con huecos justo cuando importa.

Lo que el comprobador sí hace es **enseñar el vínculo y avisar del caso que duele**: un
concepto sin ningún fragmento que lo ilustre es un concepto que el sistema no puede
citar, y eso sale como fallo.

### Y desde el 2026-08-10, el vínculo con las plantillas · `PM-C14`

Cada concepción con página tiene su **secuencia de remediación** en
[`../plantillas/`](../plantillas/LEEME.md), enlazada desde la tabla de cabecera del
concepto. **Están aparte a propósito:** esta página la corrige una docente, la secuencia la
rellena el generador.

`verificar-conceptos.py` comprueba las dos direcciones —que la secuencia exista, que esté
enlazada, y que no declare un nodo distinto del que declara su concepto—. Esa última es la
que importa: una secuencia que andamia sobre un nodo y un concepto que recupera de otro
fallaría **sin dar ningún síntoma**.

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
