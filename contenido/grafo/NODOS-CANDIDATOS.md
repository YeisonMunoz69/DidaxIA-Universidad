# Nodos candidatos · `PM-C09`

> ⚠️ **Antes de modificar nada, lea [`../../../../ANTES-DE-MODIFICAR.md`](../../../../ANTES-DE-MODIFICAR.md).**

| | |
|---|---|
| **Qué es** | La lista de trabajo para ampliar el grafo, derivada de las obras transcritas |
| **Por qué existe** | [`DD-22`](../../../04-Decisiones-de-Detalle.md) · `PM-C09` preservado en el [estado actual](../../../../ESTADO-ACTUAL.md) |
| **De dónde salen las cifras** | Inventario de cobertura ejecutado en la sesión histórica; el script no forma parte del árbol vigente y la cifra no debe presentarse como recalculable aquí |
| **Estado** | ✅ **Cerrado el 2026-08-08.** Cinco nodos nuevos escritos · cobertura 42 % → 68 % · ver §1.ter |

---

## 1. Lo que se midió, el 2026-08-07

`DD-22` avisaba de que el grafo se quedaría corto frente al corpus. Era una
estimación razonada. Ahora es una medición:

| | |
|---|---|
| Grafo | **17 nodos**: 12 de concepto y 5 concepciones erróneas · 26 aristas |
| Corpus transcrito | **5 obras · 101 archivos · 422 encabezados** de nivel 1 y 2 |
| Estructurales | **122** — «Problemas», «Contenido», «Revisión del capítulo». No reciben nodo nunca |
| Fuera del alcance comprometido | **50** — no deben recibir nodo ni indexarse |
| **Sin nodo, antes de los alias** | entre 96 y 215 |
| **Sin nodo, HOY, ya dentro del alcance** | **entre 49 y 153** |

### Por qué un rango y no una cifra

Dar un número solo sería inventar una precisión que la medición no tiene.

- **Vara estricta** — todas las palabras del nombre del nodo aparecen en el
  título: **215 sin nodo, el 72 %**. No se equivoca al decir «esto sí está
  cubierto», y se queda corta: *«Máximos y mínimos (puntos críticos)»* no casa
  con *«VALORES MÁXIMOS Y MÍNIMOS DE FUNCIONES»*, que es lo mismo.
- **Vara laxa** — basta un término distintivo: **96 sin nodo, el 32 %**. Recoge
  esos casos y a cambio casa de más: cualquier título con «derivada» le vale.

**La cifra real está entre las dos, y fijarla es leer.** Lo que ninguna de las
dos discute es la conclusión operativa: con la regla de `DD-22` —un fragmento
sin `nodo_grafo` no se indexa— **`PM-C07` no puede empezar todavía**.

---

## 1.bis. Lo que ya se hizo: alias, cero nodos nuevos

**Se eligió el arreglo que no cambia nada.** Los seis nodos que el corpus no
confirmaba estaban en los libros con otro nombre, así que recibieron un campo
`sinonimos` en `grafo.json` en vez de compañía.

| | |
|---|---|
| Nodos antes / después | **17 / 17** |
| Aristas antes / después | **26 / 26** |
| Campos previos de cada nodo | **intactos**, comprobado comparando con la copia anterior |
| Único campo nuevo | `sinonimos` |
| Pruebas | **157 pasan**, ninguna tocada |

**Es inerte para el código.** `GrafoEnMemoria` lee las claves que conoce con
`.get()` e ignora las demás; se comprobó leyendo `grafo.py`, no suponiéndolo.

Cada sinónimo sale de un título que existe en una obra. Ninguno se escribió de
memoria, que es de donde salen las listas de sinónimos que luego no aparecen en
ningún libro.

| Nodo | Sinónimos, y el título que los respalda |
|---|---|
| `N03` | «diferenciabilidad» ← *«2.2 Diferenciabilidad y continuidad»* · «derivable» ← *«Teoremas sobre las funciones derivables»* |
| `N06` | «recta tangente» ← *«La recta tangente»* · «línea tangente» ← *«Ecuaciones de la línea tangente y de la normal»* · «aproximación lineal» ← *«Aproximación lineal y recta tangente»* |
| `N07` | «tasa de variación» ← *«2.6 Derivada como tasa de variación»* · «velocidad instantánea» ← *«Velocidad promedio y velocidad instantánea»* |
| `N09` | «regla de diferenciación para el producto» ← *«2.4.6 Teorema: Regla de diferenciación para el producto»* |
| `N10` | «regla de diferenciación para el cociente» ← *«2.4.7 Teorema: Regla de diferenciación para el cociente»* |
| `N12` | «valores máximos y mínimos» ← *«Valores máximos y mínimos de funciones»* · «extremo absoluto» ← *«Aplicaciones que involucran un extremo absoluto en un intervalo cerrado»* |

### Qué consiguió y qué no

**Cuatro de los seis quedaron cubiertos** —`N03`, `N06`, `N07` y `N12`— sin
tocar la topología. `N09` y `N10` siguen a cero con vara estricta, y **por el
motivo que este documento ya predecía**: sus títulos están en nivel 3
(*«2.4.6 Teorema: …»*) y el inventario lee niveles 1 y 2.

> **Los alias solos no desbloquean `PM-C07`.** La cobertura pasó del 28 % al
> 35 % con vara estricta y el script sigue saliendo en rojo, como debe. Lo que
> queda es contenido que de verdad no existe —derivación implícita, orden
> superior, Rolle, extremos— y eso sí son nodos nuevos, que son autoría.

**Una advertencia sobre la columna laxa de `N09` y `N10`:** salen con 90, y no
significa nada. Su sinónimo contiene la palabra «derivada», que aparece en casi
todo título. Es la vara laxa haciendo lo que se dijo que hace —casar de más— y
por eso las dos cifras se publican juntas.

---

## 1.ter. Lo que se escribió el 2026-08-08 · cinco nodos y once alias

De los doce candidatos de §3.1 entraron **cinco**, y los tres tachados siguen tachados.
`N16` diferencial y aproximación lineal · `N17` derivadas de orden superior · `N18`
teorema del valor medio y de Rolle · `N19` derivada numérica y método de Newton · `N20`
función: operaciones, tipos y modelos. Cada uno lleva su campo `origen` con los títulos
que lo respaldan, y **diez aristas nuevas** los cuelgan del grafo por prerrequisito —
`N20` es prerrequisito de `N01` y `N02`; `N05` lo es de `N16`, `N17` y `N18`; `N18` lo es
de `N12`—, porque un nodo sin aristas no sirve al diagnóstico. «Tasas de variación
relacionadas» y «movimiento rectilíneo» **no** recibieron nodo: ya eran sinónimos de
`N07`, y §3.2 avisaba de que multiplicar nodos casi iguales estropea el acotado de
`ADR-002` tanto como tener pocos. `N19` funde dos candidatos por el mismo motivo.

El resto de la subida son **once sinónimos** repartidos entre nodos que ya existían, el
mayor de ellos «diferenciación» en `N05`: solo ese cubre las once apariciones de
*«DERIVADA Y DIFERENCIACIÓN»* de Leithold, que era el título sin nodo más repetido del
corpus. Resultado medido: **de 105 a 169 unidades cubiertas, del 42 % al 68 %**, y el
guion sale en 0 por primera vez. `PM-C07` queda desbloqueado.

> **Los sinónimos se derivaron leyendo la lista de unidades sin nodo que el propio
> inventario imprime, y eso hay que decirlo** porque es optimizar una medida con su
> propia salida. Lo que impide que sea circular es la regla que §1.bis ya fijaba y que
> aquí se mantiene: **cada sinónimo nombra el mismo concepto que su nodo y sale de un
> título que existe en una obra**. Dos que habrían subido la cifra se descartaron por
> incumplirlo: «funciones y sus gráficas» casaba con *«COMPORTAMIENTO DE LAS FUNCIONES Y
> DE SUS GRÁFICAS»*, que el alcance excluye por concavidad, y «diferencial» a secas
> casaba con *«Cálculo diferencial de funciones de más de una variable»*. **Cubrir de
> más en silencio material excluido es peor que no cubrirlo**, y por eso los dos casos
> quedan escritos en el campo `origen` de `N20` y de `N16`.

**Lo que sigue sin nodo, y a propósito.** Las trece unidades de *«comportamiento de las
funciones y de sus gráficas»*, *«análisis de la variación»*, asíntotas y criterio de la
primera derivada. Son el mayor montón que queda y **son las que el alcance excluye**: si
la exclusión se levantara algún día, ahí está el material esperando.

---


## 1.quater. `PM-C16`, 2026-08-14 · el campo `sinonimos` sirve a dos cosas a la vez

`PM-V13` midió el enrutamiento y dejó diez fallos por *forma genérica*, apuntando aquí. Al
recorrer las **81 formas** del grafo —etiquetas y sinónimos de los 20 nodos de concepto—
salió algo que este documento no había visto de sí mismo.

### Lo que se contó, antes de tocar nada

Cada término vale `1 / cuántos nodos lo usan` y la forma vale la suma (`jerarquico.py`
§`_peso_de_forma`, `PM-V13`). Con esa vara: **43 formas pesan menos de 2,00, 34 menos de
1,50 y solo 6 menos de 1,00**, o sea valen menos que un término que no nombre a ningún
otro nodo.

| peso | nodo | forma |
|---:|---|---|
| 0,25 | `N05` | «diferenciación» |
| 0,44 | `N05` | **«Función derivada»** *(etiqueta)* |
| 0,50 | `N05` | «derivación» |
| 0,61 | `N04` | «significado de la derivada» |
| 0,61 | `N10` | «derivada del cociente» |
| 0,75 | `N10` | **«Regla del cociente»** *(etiqueta)* |

🔴 **Y peso bajo no es etiqueta mala.** «Regla del cociente» es exactamente como se llama
el tema; puntúa bajo porque `regla` está en cuatro nodos y `cociente` en dos. La vara mide
cuánto **distingue** una forma, no si está bien escrita, y confundir las dos cosas habría
llevado a corregir el nombre correcto.

### El hallazgo: dos instrumentos leen el mismo campo y quieren lo contrario

Se midió, sinónimo por sinónimo, **cuánta cobertura del corpus cuesta quitarlo**
(`inventario-de-cobertura.py`, base 169 unidades). El resultado ordena el problema entero:

- **«diferenciación» cuesta 11 unidades.** Es la que cubre las once apariciones de
  *«DERIVADA Y DIFERENCIACIÓN»* de Leithold — la que §1.ter celebra por desbloquear
  `PM-C07`. **Y es la peor forma del grafo para enrutar: 0,25.**
- **Nueve sinónimos cuestan cero.**

Es decir: **la mejor forma para la cobertura es la peor para la identificación**, y no por
casualidad. La cobertura premia a la forma que casa **muchos títulos**; la identificación
necesita la que casa **pocas preguntas**. La regla de §1.bis —*«cada sinónimo sale de un
título que existe en una obra»*— se escribió para la primera, y desde `PM-B14` este mismo
campo alimenta la segunda. **Ningún documento lo dijo hasta hoy.**

### Qué se retiró, y qué se devolvió tras medirlo

**Dos, y solo dos:** `N09` «derivada del producto» y `N13` «derivada de una potencia».
Incumplen §1.bis —**0 encabezados de 1 355** en las cinco obras— y **cubren 0 unidades**
que su hermano documentado no cubriera ya: «regla de diferenciación para el producto»
(Leithold 2.4.6) y «regla de diferenciación de potencias» (2.4.2 y 2.4.8). Coste medido:
cobertura 169 antes y después, y las cinco cifras de recuperación idénticas.

🔴 **Y una tercera se devolvió: `N10` «derivada del cociente».** Incumple §1.bis igual, y
quitarla cuesta `Q77` — *«la derivada de un cociente es la derivada de arriba sobre la
derivada de abajo»*. **Es como lo dice un estudiante y no como lo titula un libro.** Se
conserva con el conflicto escrito en su campo `origen`, porque resolverlo es decidir para
qué sirve este campo, y eso no se decide implementando.

⛔ **`N05` no se tocó, y es el caso cabeza.** Ningún encabezado de las cinco obras dice
«función derivada», «derivada como función» ni «la derivada como…» —0 de 1 355—, así que
no hay de dónde sacar otro nombre **sin inventarlo**; y su etiqueta codifica la distinción
APOS que la separa de `N04`: `objeto` frente a `proceso`. Los diez fallos genéricos siguen
en diez, y ésa es la respuesta medida a `PM-C16`, no un pendiente.

---

## 1.quinquies. `PM-C17`, 2026-08-15 · el campo se parte en dos, y qué salió de partirlo

`D-25` tomó la opción `A` el 2026-08-14 por la noche. **Son dos listas con dos reglas
distintas, y cada instrumento lee la suya:**

| Campo | Quién lo lee | Qué exige para entrar |
|---|---|---|
| `sinonimos` | `inventario-de-cobertura.py` | **Procedencia**: sale de un título que existe en una obra — §1.bis |
| `formas_de_consulta` | `jerarquico.py` | **Distinción**: pesa ≥ 0,50 en `_peso_de_forma`, calculado sobre el grafo |

Una forma puede estar en las dos, y **59 de las 61 lo están**. Lo que la separación
resuelve son los dos extremos que §1.quater midió:

- **«diferenciación» (`N05`) se queda solo en cobertura.** Cubre 11 unidades y pesa 0,25.
- **«derivada del cociente» (`N10`) se queda solo en consulta.** No titula nada —0 de
  1 355— y gana `Q77`, que es cómo habla un estudiante.

**La etiqueta no se reparte y enruta siempre**, aunque pese poco: «Función derivada» vale
0,48 y sigue dentro, porque un nodo al que no se puede llamar por su nombre no se alcanza
por ninguna vía. Callar formas fue lo que `PM-V13` midió como caro —7 preguntas dejan de
disparar y se pierden 6 aciertos para quitar 1 fallo—, y este reparto es **un subconjunto
estricto** del más suave de aquellos pisos: mueve una forma, no tres.

⚠️ **La tabla de pesos de §1.quater es de antes de las dos retiradas** y hoy da cifras
ligeramente distintas —«Función derivada» 0,44 → **0,48**, «derivada del cociente» 0,61 →
**0,64**— porque `derivada` pasó de estar en nueve nodos a estar en siete. **El orden no
cambia y ninguna forma cruza el piso**; se anota para que nadie crea que hay dos
mediciones en desacuerdo.

### Lo que costó, medido antes y después con la base levantada

| Vara | Antes | Después |
|---|---:|---:|
| Cobertura del corpus | **169 (68 %)** | **169 (68 %)** |
| Precisión del identificador | 0,701 | **0,701** |
| Sobre las alcanzables | 0,726 | **0,726** |
| `precision_k` · `recall_nodo` · `acierto_1` | 0,571 · 0,614 · 0,515 | **iguales** |
| Reparto de causas (`PM-V11`) | 1/10/2/9/7 | **idéntico** |

🔴 **Los diez fallos por forma genérica siguen siendo diez, y no cambió ni una pregunta de
las 132.** Se dice con la cifra, y **no se ajusta el reparto hasta que bajen**: mover el
piso mirando qué preguntas se ganan sería adaptar el contenido a su propia medida, que es
lo que `D-11` y `DD-25` prohíben.

### Y por qué no bajan, que es lo que este trabajo sí averigua

`PM-C16` dejó la sospecha de que los diez venían de sinónimos pobres. **Se miró, en las
diez, qué forma gana de verdad, y no es eso:**

| Quién gana el fallo | Cuáles | Cuántos | Pesos |
|---|---|---:|---|
| Una **etiqueta**, que no se puede repartir | `Q30` `Q44` `Q80` `Q95` `Q125` | **5** | 0,48 · 1,00 · 1,14 ·2 · 2,00 |
| Una **forma de consulta** por encima del piso | `Q17` `Q53` `Q86` `Q126` | **4** | 1,14 · 1,50 ·2 · 2,00 |
| Una forma de consulta **justo en el piso** | `Q130` | **1** | 0,50 |

O sea: **la mayoría los pierde contra formas que están bien**. «recta tangente» pesa 2,00 y
nombra exactamente a `N06`; lo que pasa es que aparece dentro de una pregunta que era de
`N04`. Ninguna reclasificación por peso podía tocar eso, **y ahora está medido en vez de
supuesto**. El único caso que roza el criterio es `Q130`, donde «derivación» (0,50) gana
para `N05` una pregunta de `N20`: subir el piso lo quitaría, y por eso no se sube.

**Lo que queda apuntando fuera de este archivo** es lo que `PM-V13` ya había escrito: la
evidencia no está ni en el nombre ni en el corpus, y lo que ganaría esas preguntas es leer
**la estructura de la expresión** —lo que `D-10` descartó cuando valía dos preguntas— o la
ruta diagnóstica que `ADR-006` separó del umbral ya adoptado y remitió a calibración del OE4.

---

## 1.sexies. Lo que se escribió el 2026-08-18 · catorce nodos · `PM-C19`

**De dónde salió, y por qué no salió antes.** La indexación siguió el mapa de concepciones
erróneas de la revisión sistemática, que es **de derivadas**. Nadie cruzó el grafo contra el
**microcurrículo**, que estaba en `contenido/corpus/_obras/` desde el principio sin usar. La
consecuencia se midió el 2026-08-18: de los 203 fragmentos, `N01` (Límite), `N02` (Continuidad)
y `N12` (Máximos y mínimos) tenían **cero**, y preguntar *«¿qué es un límite?»* devolvía
procedencia `sin-fuente`.

> **No era un fallo del recuperador.** El umbral de 0,70 y la regla `U3` de `ADR-006` —*«más
> vale sin contexto que con contexto irrelevante»*— funcionaban bien: el sistema decía la
> verdad. Faltaba el material.

**Los catorce, `N21`–`N34`.** El último identificador pasa de `N20` a **`N34`**.

| Corte | Nodos |
|---|---|
| Primer corte · límites y continuidad | `N21` laterales · `N22` teoremas de límites · `N23` al infinito e infinitos · `N24` asíntotas · `N25` tipos de discontinuidad · `N26` valor intermedio · `N27` trigonométricos · `N28` sándwich · `N29` formas indeterminadas |
| Tercer corte · derivada y aplicaciones | `N30` implícita · `N31` L'Hospital · `N32` razones relacionadas · `N33` monotonía y 1ª derivada · `N34` concavidad y 2ª derivada |

Con **21 aristas** de prerrequisito. Ningún nodo existente se tocó salvo lo que se dice abajo.

### Lo que NO recibió nodo, y por qué

- **La unidad 1 entera (Funciones)** cabe en `N20`: definición, dominio y rango, evaluación,
  producto cartesiano, tipos, álgebra, y exponencial/logarítmica/inversa. Trocearla serían seis
  nodos que una docente tendría que volver a fusionar — el aviso de §3.2 sobre multiplicar
  nodos casi iguales.
- **Recta tangente y normal** → `N06`. **Optimización** → `N12`. **Derivabilidad y
  continuidad** → `N03`.

### Tres decisiones que contradicen algo escrito, y hay que mirarlas

**1 · La etiqueta de `N28` dice «sándwich», no «emparedado».** El microcurrículo dice
«Teorema del emparedado». Dos motivos para apartarse: en el español de Colombia se dice
**sándwich**, y sobre todo **«emparedado» no aparece en ningún encabezado de las cinco obras**
—cero de 1 355—, así que incumpliría §1.bis. Los dos que sí están: *«TEOREMA 1.3 (Teorema de
estricción / Sándwich)»* y *«1.10.1 El teorema de estricción»*.

**2 · `N28` es prerrequisito de `N27`, aunque el programa los liste al revés.** El
microcurrículo pone «Límites trigonométricos» antes que «Teorema del emparedado», pero es con
el sándwich con lo que se demuestra `lim sen(x)/x = 1`.

**3 · `N31` usa «L'Hospital» y no «L'Hôpital».** Es la grafía del corpus —*«3.8. Cálculo de
límites indeterminados - Regla de L'Hospital»*— y la que el estudiante leerá en su libro. Cero
encabezados con «Hôpital».

### El efecto colateral que hubo que resolver, y es interesante

Añadir catorce nodos **cambió el peso léxico** de `_peso_de_forma`, que vale `1 / nº de nodos
que usan el término`. Dos formas que ya enrutaban estaban **exactamente en el piso de 0,50**,
sin margen, y un tercer dueño las hundió:

| Forma | Dueños antes | Después | Peso |
|---|---|---|---|
| `N10` «derivada del cociente» | N04, N10 | + `N22` | 0,50 → 0,44 |
| `N05` «derivacion» | N05, N19 | + `N30` | 0,50 → 0,33 |

Resuelto aplicando la regla que `D-25` ya tenía escrita —*«o baja el piso con su medición, o
sácalas de `formas_de_consulta`»*—, y por el lado que menos daño hace en cada caso:

- **`N22` cede**: «límite del cociente» sale de enrutamiento y se queda en `sinonimos`. Es el
  nombre de un teorema, no como pregunta un estudiante. `N10` recupera su peso y el ejemplo que
  `D-25` consagra sigue intacto.
- **`N05` cede**: «derivacion» a secas sale de enrutamiento. ⚠️ **Es el único nodo existente
  que `PM-C19` modifica**, y conviene que una docente lo mire: quien escriba solo «derivación»
  ya no cae en `N05`. Sigue en `sinonimos`, así que **deja de enrutar, no deja de contar**.

**La lección, que vale para el siguiente que amplíe el grafo:** una forma en el piso exacto no
tiene margen, y el grafo crece. `pruebas/unidad/test_grafo.py` lo detectó al instante — es el
comprobador haciendo justo lo que `COMO-TRABAJAMOS.md` §4 pide.



## 1.septies. Lo que se escribió el 2026-08-19 · el material · `PM-C21`

**68 fragmentos nuevos, `F-206` a `F-273`.** El corpus pasa de **203 a 271** escritos y de
**180 a 248** indexados, y la cobertura del grafo de **17/34 a 34/34**. La cuenta la
reproduce `contenido/corpus/verificar-cobertura.py`, que se escribió antes a propósito.

### Tres cosas que la noche encontró y que no eran el encargo

**1 · El índice de producción estaba VACÍO.** Cero filas en `fragmento`, con 14 turnos ya
registrados en `historial_turno`. La ingesta nunca se había corrido contra esa base. Es
decir: **no era que faltara material de límites, es que no había material de nada** — toda
pregunta, de cualquier tema, caía en `sin-fuente`. Lo que lo ocultaba es que todos los
comprobadores cuentan **archivos**, y un corpus escrito y no ingerido se parece desde fuera
a uno que sí está. Por eso `verificar-cobertura.py --indice` existe ahora.

**2 · «emparedado» sí está en el corpus.** La revisión de `PM-C19` miró **encabezados** y
concluyó bien que ahí no aparece; pero en el **cuerpo** de Purcell está ocho veces, y es el
término que usa esa obra —la que aporta 97 de los 203 fragmentos originales— y también el
del microcurrículo. Sin esa forma, *«qué dice el teorema del emparedado»* **no enrutaba a
ningún nodo**. Se añadió a `formas_de_consulta` de `N28`. La etiqueta sigue diciendo
«sándwich» por §1.bis: **enrutar y etiquetar son cosas distintas**, y sólo la segunda
depende de los encabezados.

**3 · Dos preguntas del primer corte no enrutaban, y no por culpa de `PM-C19`.**

| Pregunta | Iba a | Por qué |
|---|---|---|
| «qué es un límite lateral» | `N01` | La etiqueta «Limite» está contenida en la pregunta, y las formas de `N21` estaban todas en plural o decían «unilateral» |
| «cuándo una función es continua» | **ningún nodo** | `N02` sólo ofrecía «funciones continuas» |

Se añadieron formas en **singular y en el habla del estudiante**. La regla 1 del
identificador toma la forma **más larga**, así que «limite lateral» gana a «Limite». Ninguna
forma quedó por debajo del piso de `D-25`.

### La cifra de la noche

No es el número de archivos. Es ésta, medida contra el índice real de producción con las
cinco preguntas que se acordaron:

| | antes | después |
|---|---|---|
| filas en `fragmento` | **0** | **248** |
| preguntas en `sin-fuente` | **5 de 5** | **0 de 5** |

Las cinco responden con similitudes entre **0,81 y 0,86**, sobre el umbral de 0,70 de
`ADR-006`.

### ⚠️ Lo que hay que mirar mañana

- **Los metadatos son de primera pasada.** `nivel_apos` y `registro_duval` de los 68 son
  **juicio pedagógico, no dato del texto**. Se pusieron con criterio y **no están
  establecidos**: los valida una docente.
- **`concepcion_asociada` va vacío en los 68.** El catálogo `M01`–`M24` no tiene página para
  las de límite. En particular **`M01` —«límite: concepción dinámica frente a ε-δ», la de
  frecuencia más alta de todo el catálogo—** está excluida, y el motivo escrito en
  `MAPA-M01-M24.md` es que darle página *«obligaría a trocear corpus de límite»*. **Ese
  corpus ya existe.** Asignarla es una decisión, y no se tomó aquí.
- **El alcance comprometido dice otra cosa.**
  `ERS-Objetivo1/1-ALCANCE-COMPROMETIDO/01-Definicion-del-Alcance.md:63` declara límite y
  continuidad *«únicamente como prerrequisito declarativo»*, y su columna «excluido» incluye
  extremos, concavidad y derivación implícita — que son `N12`, `N33`, `N34` y `N30`. **No se
  tocó ese documento.**
- **«qué es un límite» recupera fragmentos de `N21`**, no de `N01`. El acotado incluye
  vecinos del grafo, y es el defecto que `PM-V04` ya midió: los prerrequisitos bajan
  `acierto_1` de 0,833 a 0,667. Responde bien, pero no con el material más directo.


## 2. Los seis nodos, y por qué el corpus no los confirmaba

> **Esta tabla es el diagnóstico ANTES de los alias**, y se conserva porque
> explica por qué se eligió ese arreglo. Las cifras de hoy están en §1.bis: no
> se actualizan aquí a propósito, para que no parezca que el diagnóstico se
> escribió sabiendo ya el resultado.

| Nodo | Estricta | Laxa | Qué está pasando |
|---|:--:|:--:|---|
| `N06` Pendiente de la recta tangente | 0 | 8 | **Nombre.** Los libros titulan «Recta tangente y derivada» |
| `N07` Tasa de cambio | 0 | 1 | **Nombre.** Los libros dicen «Tasas de variación» y «Derivada como tasa de variación» |
| `N03` Derivabilidad | 0 | 0 | Se trata dentro de otras unidades, sin titular propio |
| `N09` Regla del producto | 0 | 0 | **Nivel.** Vive dentro de «Derivada y diferenciación», por debajo del nivel 2 |
| `N10` Regla del cociente | 0 | 0 | Igual que `N09` |
| `N12` Máximos y mínimos (puntos críticos) | 0 | 0 | **Nombre.** Los libros dicen «Valores máximos y mínimos de funciones» |

**Tres causas distintas y tres arreglos distintos.** Cuatro son de nombre y se
arreglan añadiendo sinónimos al nodo, sin tocar el grafo — **hecho, y funcionó
en los cuatro**. Dos son de nivel: el
inventario mira encabezados de nivel 1 y 2 porque ahí es donde el libro puso sus
unidades, y las reglas de derivación viven un escalón más abajo.

> **Esto es una limitación declarada del inventario, no un hallazgo sobre los
> libros.** Que `N09` salga a cero no significa que ninguna obra explique la
> regla del producto; significa que ninguna le dedicó una sección con ese
> título. Antes de tocar `N09` hay que mirar el nivel 3.

---

## 3. Candidatos, con la procedencia de cada uno

Salen de títulos que están en las obras. **Ninguno viene de recordar un programa
de cálculo**, que es de donde salen las listas que luego no casan con el
material.

> ### ⚠️ Tres de los doce candidatos originales estaban excluidos por escrito
>
> Al leer la tabla §3 de
> [`01-Definicion-del-Alcance.md`](../../../../ERS-Objetivo1/1-ALCANCE-COMPROMETIDO/01-Definicion-del-Alcance.md)
> resultó que su columna **«Excluido del compromiso»** nombra tres de los que
> esta lista proponía: **derivación implícita**, **puntos críticos y extremos
> locales**, y **concavidad**.
>
> Proponerlos habría **ampliado el compromiso del proyecto por descuido**. Van
> tachados abajo, y el inventario ya los aparta solo.

### 3.1 Los que el corpus pide con más insistencia

| Candidato | Títulos que lo respaldan |
|---|---|
| **Diferencial y aproximación lineal** | «Derivada y diferencial» ·2 · «Concepto de diferenciales» · «Aproximación lineal y recta tangente» · «Fórmulas de diferenciación en notación de Leibniz» |
| **Derivadas de orden superior** | «Derivadas de orden superior» ·2 · aparece en **5 obras** al mirar todos los niveles |
| **Teorema de Rolle y del valor medio** | «Teorema de Rolle y teorema del valor medio» ·2 · presente en **6 archivos** |
| ~~**Extremos absolutos en intervalo cerrado**~~ **EXCLUIDO** · la tabla del alcance excluye «puntos críticos, extremos locales» | «Aplicaciones que involucran un extremo absoluto en un intervalo cerrado» ·2 · «Aplicaciones adicionales sobre extremos absolutos» ·2 |
| ~~**Trazado de gráficas y comportamiento de funciones**~~ **EXCLUIDO** · la tabla excluye «concavidad» | «Comportamiento de las funciones y de sus gráficas» ·4 · «Resumen para el trazo de las gráficas de funciones» ·2 · concavidad e inflexión en **3 archivos** |
| **Tasas de variación relacionadas** | «Tasas de variación relacionadas» ·2 |
| **Movimiento rectilíneo** | «Movimiento rectilíneo» ·2 — **puede fundirse en `N07`** en vez de ser nodo propio |
| **Método de Newton** | «Aproximaciones mediante el método de Newton…» ·2 · **6 secciones** en 4 obras |
| ~~**Derivación implícita**~~ **EXCLUIDO** · nombrada literalmente en la columna de exclusiones | «Derivación implícita» ·3 |
| **Derivada numérica** | «Derivada numérica» ·2 |
| **Funciones logarítmicas y exponenciales** | **3 y 7 secciones** respectivamente, en 4 obras |
| **Función: operaciones, tipos y modelos** | «Operaciones con funciones y tipos de funciones» ·2 · «Funciones como modelos matemáticos» ·2 |

### 3.2 Lo que hay que decidir antes de escribir ninguno

1. **Cuáles son nodo y cuáles son sinónimo.** «Movimiento rectilíneo» y
   «Derivada como tasa de variación» probablemente sean `N07` con otro nombre.
   Multiplicar nodos casi iguales estropea el acotado de `ADR-002` tanto como
   tener pocos.
2. **`N06`, `N07` y `N12` necesitan alias antes que compañía.** Es más barato y
   arregla ocho, uno y varios casos respectivamente sin tocar la topología.
3. **Las aristas de prerrequisito.** Un nodo sin aristas no sirve al
   diagnóstico. Salen de la prosa de los conceptos, según [`../conceptos/LEEME.md`](../conceptos/LEEME.md).

---

## 4. Lo que queda fuera, y ya no hay que cribar a mano

**El inventario lo aparta solo**, y no porque alguien escribiera la lista: lee
la columna «Excluido del compromiso» de la tabla del alcance. Si el alcance
cambia, la criba cambia con él.

| Motivo | Unidades | De dónde sale |
|---|:--:|---|
| Excluido en la tabla del alcance | 10 | Leído de `01-Definicion-del-Alcance.md` §3 |
| Cálculo integral | 9 | Escrito en el script, con su motivo |
| Geometría del espacio · vectores | 8 | Íd. |
| Números complejos y polinomios | 12 | Íd. |
| Paramétricas y polares | 9 | Íd. |
| Sucesiones y series | 1 | Íd. |
| **Total** | **50** | |

**Doce de esas frases están escritas en el script y no leídas**, porque ninguna
tabla del proyecto nombra «vectores en el espacio»: a nadie se le ocurrió
excluir explícitamente algo tan ajeno. Cada una lleva su motivo escrito al lado,
que es lo mínimo exigible cuando algo no se puede derivar.

### Una lección de esta pasada

La primera versión sacaba **una palabra** de cada frase excluida, y produjo tres
exclusiones falsas: «logarítmica», «diferenciales» y «variables». Las derivadas
de funciones logarítmicas **están comprometidas**, en la columna de al lado.

> Excluirlas por compartir una palabra con lo que no está comprometido habría
> sacado del corpus material prometido, **y en silencio**. Una palabra no es un
> tema: ahora se exige la frase entera.

---

## 4.bis. Una tensión entre documentos, que no se resuelve aquí

**`N12` del grafo se llama «Máximos y mínimos (puntos críticos)».** La tabla del
alcance excluye del compromiso «puntos críticos, extremos locales y concavidad».

Las dos cosas están escritas y no encajan. Tres datos, sin conclusión:

- El nodo existe desde antes que la criba y **cinco unidades del corpus lo
  respaldan** con títulos del tipo «Valores máximos y mínimos de funciones».
- «Excluido del compromiso» **no es lo mismo que prohibido**: el proyecto puede
  cubrir de más, lo que no puede es prometerlo.
- Si `N12` se queda, conviene que su etiqueta **no diga «puntos críticos»**,
  porque es la expresión literal que el alcance excluye.

**Es de los autores.** Cambiar la etiqueta de un nodo o retirar una exclusión
del alcance son decisiones de compromiso, no de script.


## 5. Cómo volver a medir esto

```powershell
# desde la raíz del repositorio, la carpeta que contiene CONTEXTO-MAESTRO.md
python OE3-Implementacion\codigo\contenido\grafo\inventario-de-cobertura.py
```

Sale con error mientras más de la mitad de las unidades no tenga nodo, que es la
condición que `DD-22` puso para que `PM-C07` pueda empezar. **Al añadir nodos o
alias, se vuelve a ejecutar y la cifra se mueve sola**: no hay ningún número
escrito dentro del script.

---

## 6. Lo que este documento no hace, y conviene no dar por hecho

- **No añade ni un nodo al grafo.** `grafo.json` está intacto.
- **No mira el nivel 3.** Las reglas del producto y del cociente viven ahí y
  quedan sin confirmar.
- **No consultó a las docentes.** La ordenación de un grafo pedagógico es
  justamente lo que `PM-X01` les pide, y esta lista es material para esa
  conversación, no un sustituto.
- **No decide cuántas concepciones del mapa se comprometen.** El propio mapa
  dice que ese número sale de medir, no de la lista.

---

*`PM-C09` · `DD-22` · Fabián Armando Hoyos Cerón · Yeison Javier Muñoz Gómez*
