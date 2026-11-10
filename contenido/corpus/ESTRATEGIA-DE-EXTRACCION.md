# Estrategia de extracción del corpus

> ⚠️ **Antes de modificar nada, lea [`../../../../ANTES-DE-MODIFICAR.md`](../../../../ANTES-DE-MODIFICAR.md).**

| | |
|---|---|
| **Qué es** | Qué hacer con cada obra para convertirla en fragmentos, y por qué |
| **Base** | Muestreo directo de las diez obras de [`_obras/`](_obras/), 2026-08-05 |
| **Ficha de cada obra** | [`FUENTES.md`](FUENTES.md) |
| **Estado** | 🟢 2026-08-06 · **transcripción manual completa de las cinco obras** · el troceo a fragmentos **no ha empezado** |

---

## 1. El hallazgo que decide todo lo demás

Se extrajo el enunciado de la regla de la cadena del **mejor caso posible del lote**: un
PDF generado por LaTeX, con prosa impecable y sin escaneo de por medio.

```
teorema 2.4 (Regla de la cadena.) ... Además la derivada de f es:
 0
 0
0
f (x) = g (h(x)) h (x).
```

El enunciado correcto es `f'(x) = g'(h(x)) · h'(x)`. Las primas salieron como ceros en
líneas sueltas y **delante** de la función a la que pertenecen. La notación de Leibniz de
la misma página salió repartida en seis renglones.

> ### Si el PDF mejor construido del lote pierde la fórmula, ninguna tubería la recupera de los demás.

De ahí sale la regla de trabajo:

> ### La prosa se extrae. La matemática se transcribe.

**Y no es una concesión, porque `DD-02` ya obliga a verificar la matemática al ingerir.**
Toda fórmula va a pasar por una comprobación de todas formas. Una extracción automática
que después hay que revisar entera ahorra menos de lo que aparenta.

**Consecuencia sobre la elección de obras, y es la menos evidente.** Si la matemática se
transcribe siempre, **la calidad con que una obra renderiza sus fórmulas deja de ser un
criterio para elegirla**. Lo que queda como criterio es la calidad de la prosa, el ajuste
pedagógico, que esté en español y lo que cueste localizar el pasaje.

### El orden de magnitud, que es lo que hace viable transcribir

Con del orden de diecisiete conceptos y entre diez y treinta fragmentos cada uno, salen
**cientos de fórmulas, no decenas de miles**. Es trabajo acotado y medible. La cifra real
saldrá de `C-M21`, que es el primero que se carga entero justamente para medirlo, como
`DD-13` exige antes de comprometer el resto.

---

## 2. Diagnóstico obra por obra

Los datos vienen de muestrear cada archivo, no de su extensión ni de su reputación.

| Clave | Capa de texto | Prosa | Matemática | Estructura detectable | Veredicto |
|---|---|---|---|---|---|
| **`LOP`** | Nativa, de LaTeX | Excelente | Dispersa en líneas sueltas | **Muy alta**: 99 teoremas, 117 ejercicios, 53 secciones | ✅ **Empezar aquí** |
| **`PUR`** | Nativa, editorial | Excelente | **Sustituida por glifos, en su sitio** | Alta: secciones rotuladas | ✅ **Empezar aquí** |
| **`SWO`** | OCR de Internet Archive | Legible con erratas | Muy degradada | Media | ✅ **Útil**: el escaneo cubre justo el cálculo diferencial |
| **`LEI`** | **Ninguna** · escaneo a ~300 ppi | — | — | — | ⬜ Aplazada |
| **`SPI`** | **Ninguna** · escaneo a 400 ppi | — | — | — | ⬜ Aplazada |
| **`PIS`** | OCR de Acrobat sobre edición de 1977 | **Inservible** | Inservible | — | ❌ Descartada |

### `LOP` · López Erazo, Unicauca

**Es la fuente con mejor procedencia del lote**: Departamento de Matemáticas de la
Universidad del Cauca, enero de 2023, en español. Su estructura es la más explotable
—`teorema 2.4`, `EJERCICIO 2.17`, `Observación 56`— lo que permite localizar un pasaje
sin leer el libro entero.

**Pero su propio autor acota para qué sirve:** *«el trabajo no es de carácter teórico y
por ello… no profundizaré en la teoría»*. Son unos 800 ejercicios y problemas con algunas
definiciones y teoremas.

> Sirve para **«Cómo se manifiesta»** y para los ejemplos trabajados. Para **«La
> explicación»** hace falta otra obra.

**Un requisito técnico concreto.** El PDF emite `ı` (i sin punto, U+0131) seguido de un
acento combinante en vez de `í`, y descompone el resto de acentos. `Límites` no se
encuentra buscando `Límites`, y `Observación` aparece 0 veces sin normalizar y 205 veces
después. **Toda extracción de `LOP` normaliza a NFC y sustituye `ı`+acento por `í` antes
de cualquier otra cosa.** Es un artefacto conocido de LaTeX y se corrige una vez.

### `PUR` · Purcell, Varberg y Rigdon, 9.ª edición

Prosa excelente y didáctica, que es lo que el banco de conceptos necesita para explicar.

Su matemática está **sustituida glifo a glifo, pero en su posición**, lo que la hace
legible por una persona y parcialmente recuperable por máquina. El patrón se verificó por
conteo sobre las 519 páginas:

| En el texto extraído | Significa | Ocurrencias comprobadas |
|---|---|---|
| `F¿(x)` | `F'(x)` — la prima | 51 en formas `X¿(x)` |
| `sen1at2` | `sen(at)` — `1` abre y `2` cierra | patrón consistente |
| `p>2` | `π/2` — `>` es la barra y `p` es π | 210 solo esta forma |
| `2x2` | `2x²` — el exponente se aplana | frecuente |

> ⚠️ **El mapa no se aplica a ciegas.** `1` y `2` también son dígitos legítimos:
> `2x2 - 4x + 1` mezcla dígitos reales con un exponente aplanado. Sirve para **leer** el
> pasaje sin abrir el PDF, no para convertir sin mirar.

### `SWO` · Swokowski, 2.ª edición

El OCR de Internet Archive deja la prosa legible con erratas ocasionales y la matemática
bastante rota (`f(x) = nx”` por `f'(x) = nx^{n-1}`).

**El escaneo es parcial, y resulta que a favor.** La obra impresa tiene 1 168 páginas y
el archivo llega hasta la **página 227**: funciones, límites, la derivada y valores
extremos. Es el cálculo diferencial completo y nada más. Para este proyecto, un escaneo
de la obra entera no habría aportado nada adicional.

> **Paginación: `página impresa = hoja del PDF − 17`.** Comprobado en cinco puntos.

Sube de «utilizable con reservas» a **tercera fuente de consulta habitual**.

> ⚠️ **Corrección.** La primera versión de este documento decía que el escaneo era a doble
> página. Se dedujo del tamaño del PDF sin comprobarlo y era falso. Se corrigió al
> verificar los encabezados hoja por hoja, y en la misma comprobación apareció lo del
> alcance parcial, que nadie sospechaba.

### `LEI` y `SPI` · aplazadas, y no por su calidad

Son **2 300 páginas sin capa de texto ninguna**. Los escaneos son buenos —`SPI` a 400 ppi
bitonal, `LEI` a ~300 ppi— así que el OCR es viable; lo que no es viable hoy es el
calendario.

Se probó `SPI` con Tesseract sobre una página al azar. Con el modelo **inglés**, único
instalado en el entorno de prueba, la prosa salió reconocible y la matemática no:

```
si |y - z| <6, entonces [f(x) -f(z)| <¢
```

donde `δ` se leyó `6`, `ε` se leyó `¢` y `|f(y)` se leyó `[f(x)`. **Las letras griegas y
los símbolos matemáticos se confunden de forma sistemática.** Con el modelo español la
prosa mejoraría; la matemática, no — y la matemática ya estaba previsto transcribirla.

> **Requisito si se retoman:** instalar `tesseract-ocr-spa`. En el entorno de prueba solo
> estaba `eng`, y sin el modelo español los acentos se pierden.

**Y hay un motivo de fondo para no empezar por `SPI`.** El pasaje muestreado es una
demostración ε-δ de continuidad uniforme. Spivak es un texto de análisis riguroso: para
explicarle a un estudiante que no reconoce una composición, Purcell y Leithold ajustan
mejor. La obra más respetada del lote es la menos indicada para este uso concreto.

### `PIS` · descartada

Las tres copias son OCR de la edición Mir de 1977 y las tres son inservibles:

```
~10 se deducedequelg:.-CX>,eua.noo:\lende(l~ valorea
```

El `.epub` no está mejor: `f” (2) <0 cuando z<a` donde debería decir `f''(x) < 0 cuando
x < a`. **No es cuestión de limpiar erratas: la variable se convirtió en otra cosa.**
Volver a pasar OCR sobre el escaneo original produciría mejor resultado que partir de
este texto, y aun así la obra no aporta nada que `LOP` y `PUR` no cubran en español y con
menos esfuerzo.

---

## 2.bis Herramientas de conversión · qué usar y qué no esperar de ellas

> **Añadido el 2026-08-06**, tras preguntarse cómo se procesan las obras sin transcribirlas
> a mano una por una.

### La pregunta correcta no es cuál convierte mejor, sino cuánto hay que convertir

**No hacen falta las 4 700 páginas.** Hacen falta las que sostienen los dieciséis conceptos
del [`MAPA-M01-M24.md`](../conceptos/MAPA-M01-M24.md). `C-M21` se resolvió con **dos
páginas**: Purcell 119 y López Erazo 86. Si el resto se comporta parecido, hablamos de
**entre treinta y sesenta páginas en total**, no de miles.

> ### Convertir sesenta páginas es viable en un portátil. Convertir cuatro mil setecientas es otro proyecto.

Eso cambia la decisión entera: la herramienta deja de tener que ser rápida y barata a
escala, y solo tiene que ser **buena en las páginas que importan**.

### Localizar antes de convertir

| Obra | Cómo se localiza el pasaje | Costo |
|---|---|---|
| `LOP` | Búsqueda de texto: `teorema 2.4`, `EJERCICIO 2.17` | Segundos |
| `PUR` | Búsqueda de texto por rótulo de sección | Segundos |
| `SWO` | Búsqueda sobre el OCR existente, con `página = hoja − 17` | Segundos |
| `LEI` · `SPI` | **Índice de la obra**, porque no hay capa de texto | Minutos, a mano |

Las tres primeras se localizan con `pdftotext`, que ya está en cualquier equipo. Solo las
dos aplazadas exigen abrir el libro.

### Las herramientas, y para qué sirve cada una

Todas son de código abierto y se ejecutan en el equipo, sin servicio de pago.

| Herramienta | Qué hace | Cuándo conviene |
|---|---|---|
| **MinerU** | Detecta la disposición de la página, reconoce fórmulas y las emite en LaTeX. Produce Markdown | **La opción por defecto** para páginas escaneadas o con codificación rota |
| **Marker** | Lo mismo, con otra familia de modelos | Alternativa si MinerU falla en una obra concreta |
| **Docling** | Conversión a Markdown con comprensión de fórmulas | Alternativa. Licencia permisiva |
| `pdftotext` | Extrae la capa de texto tal cual | **Prosa** de `LOP` y `PUR`, que ya sale bien |
| Tesseract | OCR de texto, sin matemática | No resuelve el problema que tenemos |

> ⚠️ **Ninguna de las tres se ha probado sobre estas obras.** El entorno de trabajo de esta
> sesión no pudo instalarlas: `pip install docling` arrastra los paquetes de **CUDA**
> —cientos de megabytes cada uno— y agotó el disco. **Lo que sigue son criterios de
> elección, no resultados.**

### Dos cosas prácticas que sí se comprobaron

**Instalar la versión de CPU primero.** Por omisión, estas herramientas descargan la
construcción de PyTorch para tarjetas NVIDIA. `DD-17` deja constancia de que los portátiles
del equipo tienen 4 GB de memoria de vídeo, insuficientes de todos modos, así que esos
paquetes son varios gigabytes que no se van a usar:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install mineru
```

**En `PUR`, convertir la imagen puede ser mejor que leer el texto.** Su capa de texto está
**mal codificada** —`F¿(x)` por `F'(x)`, `p>2` por `π/2`—, de modo que una herramienta que
lea esa capa hereda el error. Una que renderice la página y reconozca la fórmula **no pasa
por la codificación rota**. Es contraintuitivo y conviene probarlo antes de decidir.

### La prueba de aceptación, antes de convertir nada más

**Se convierten las dos páginas que ya están transcritas a mano** —`PUR` 119 y `LOP` 86— y
se compara la salida contra los seis fragmentos de `C-M21`, que hacen de verdad de
referencia.

| Qué se mira | Qué contaría como aprobado |
|---|---|
| Las once fórmulas de esas dos páginas | Cuántas salen en LaTeX **equivalente**, comprobado con SymPy y no a ojo |
| La prosa | Sin palabras perdidas ni acentos rotos |
| El esfuerzo de corrección | **Menor que transcribir de nuevo.** Si corregir cuesta lo mismo, la herramienta no aporta |

> **Ese último criterio es el que decide.** Una herramienta que acierta el 70 % de las
> fórmulas obliga a revisarlas todas igualmente, porque no se sabe cuál es del 30 %
> restante. Lo que se mide no es su acierto: es **cuánto trabajo ahorra sobre transcribir**.

**Y `DD-02` no se relaja en ningún caso.** Toda fórmula se comprueba al ingerir, venga de
una herramienta o de un teclado. La conversión automática cambia de dónde sale el borrador,
no si se verifica.

---

## 3. El procedimiento por fragmento

Cuatro pasos, y el tercero es el que impide que se cuele una fórmula equivocada.

1. **Localizar** el pasaje por la estructura de la obra —`teorema 2.4` en `LOP`, el
   rótulo de sección en `PUR`— y no leyendo linealmente.
2. **Extraer la prosa** con `pdftotext`, normalizar a NFC y corregir los artefactos
   conocidos de esa obra.
3. **Transcribir la matemática a mano**, mirando la página renderizada y no el texto
   extraído. Se marca `captura: mixta` en la procedencia.
4. **Verificar la fórmula** según `DD-02`, antes de que el fragmento entre al corpus.

> **El paso 3 mira la página, no el texto extraído.** Es la diferencia entre transcribir
> lo que el libro dice y transcribir lo que el extractor entendió. En `LOP` las primas
> salen delante de su función: quien copie del texto extraído escribirá la fórmula al
> revés sin notarlo.

### El campo `captura`

| Valor | Qué significa |
|---|---|
| `nativa` | Prosa y fórmula salieron del texto del PDF sin intervención |
| `mixta` | Prosa extraída, **fórmula transcrita a mano** ← el caso normal |
| `ocr` | La prosa viene de OCR y se revisó |
| `manual` | Todo transcrito a mano |

Existe para poder responder después *«¿de dónde salió este signo?»* sin volver a abrir el
libro, y para saber qué habría que revisar si un día aparece un error sistemático.

---

## 4. Orden de trabajo propuesto

> ## ⚠️ Este orden quedó superado el 2026-08-06 · ver §4.bis
>
> Se escribió cuando el plan era extraer la capa de texto. **Al medir con MinerU sobre cinco
> páginas, la clasificación se invirtió**: la obra sin capa de texto salió la mejor y la que
> ya traía OCR salió la peor. Se conserva sin reescribir para que se vea qué se creía antes
> de medir.

| | Obra | Para qué |
|:--:|---|---|
| 1 | **`PUR`** | La explicación teórica de cada concepto |
| 2 | **`SWO`** | Segunda voz de la explicación. Su escaneo cubre justo el cálculo diferencial |
| 3 | **`LOP`** | Ejemplos, ejercicios y formas concretas del error |
| — | `LEI` · `SPI` | Solo si aparece un vacío que lo justifique, y con OCR previo |
| — | `PIS` | No se usa |

---

## 4.bis Orden vigente · medido sobre cinco páginas el 2026-08-06

**Lo que decide no es la obra sino el tipo de fuente**, y el resultado es contraintuitivo:

| Tipo de fuente | Obra probada | Cómo salió |
|---|---|---|
| **Escaneo SIN capa de texto** | `LEI` p. 164 | ✅ **El mejor.** Teorema, ejemplos y ecuaciones numeradas, todo correcto |
| PDF de LaTeX | `LOP` p. 86 | ✅ Fórmulas correctas · ⚠️ prosa con el acento separado |
| PDF editorial con capa de texto | `PUR` p. 118 y 119 | ✅ Correcto salvo **dentro de recuadros** |
| **Escaneo CON OCR previo** | `SWO` p. 131 | ❌ **El peor, y del modo más peligroso** |

### Por qué el que no tenía texto salió mejor

**Porque MinerU no puede equivocarse de fuente.** Sin capa de texto solo le queda mirar la
página; con capa de texto, a veces la prefiere — y si esa capa está mal codificada, hereda
el error. Fue justo lo que pasó en el recuadro del Teorema A de `PUR`, donde salió
`(f g)<sup>¿</sup>(x)` con el glifo roto intacto.

> **El motivo por el que `LEI` y `SPI` estaban aplazadas ha desaparecido.** Se apartaron
> porque `pdftotext` no devolvía nada de ellas. MinerU no usa `pdftotext`. **Vuelven a
> estar en juego, y en primera posición.**

### Por qué `SWO` es el caso peligroso

No falla de forma visible: **produce LaTeX plausible y matemáticamente falso.**

| Lo que la página dice | Lo que MinerU escribió |
|---|---|
| `dy/dx = (dy/du)(du/dx)` | `\frac{dy}{dx} = \frac{dy}{dy}\frac{du}{dx}` |
| `f'(u)` | `f^{*}(u)` |
| `y = f(u), u = g(x)` | `y \in (\mathcal{U}), u = \mathcal{u}(\mathcal{x})` |
| «Regla de la Cadena» | «Regta de la Cadena» |

`dy/dy` en lugar de `dy/du` **parece una fórmula** y pasa una mirada rápida. Es peor que un
error evidente, porque no pide revisión.

### Orden vigente

| | Obra | Condición de uso |
|:--:|---|---|
| **1** | **`LEI`** Leithold | Ninguna especial. Es la que mejor se comporta |
| **2** | **`PUR`** Purcell | **Revisar todo lo que esté dentro de un recuadro** |
| **3** | **`LOP`** López Erazo | **Corregir el acento separado** antes de ingerir |
| **4** | `SPI` Spivak | Sin probar. Mismo tipo de fuente que `LEI`, así que debería comportarse igual — **hay que comprobarlo** |
| — | **`SWO`** Swokowski | **Solo si ninguna otra cubre el pasaje**, y verificando fórmula por fórmula contra la página |
| — | `PIS` Piskunov | No se usa |

> **`SWO` no se descarta, se degrada.** Su escaneo cubre exactamente el cálculo diferencial
> y puede hacer falta para algún pasaje. Lo que ya no es cierto es que ahorre trabajo.

**`PUR` y `SWO` van primero por una razón que no es técnica:** las dos figuran en la
**bibliografía oficial del microcurrículo** del curso, junto con `LEI` y `PIS`. Un
fragmento que sale de ahí no necesita que el equipo justifique por qué eligió esa obra.

`LOP` no está en esa bibliografía y es de otra institución —Universidad del Cauca, no
Colegio Mayor—, así que entra por su calidad y su estructura, no por prescripción. Y su
autor declara que no desarrolla la teoría: pesa en ejemplos y ejercicios, no en la
explicación.

**Se empieza por `C-M21`**, que ya está escrito, para medir el costo de un concepto antes
de comprometer los demás. Es la condición que `DD-13` puso y que todavía no se ha
cumplido.

---

## 4.ter Qué pasó de verdad · contado el 2026-08-10, con `PM-C07` agotado

> **Capa fechada. No reescribe §4 ni §4.bis: dice qué hizo el corpus cuando se armó, y
> cierra las dos cosas que quedaron sin constancia.** Los recuentos salen de contar el
> campo `obra:` de los 203 fragmentos, no de recordar.

| Obra | Fragmentos | Puesto en **§4.bis** | ¿Encaja? |
|---|---:|:--|:--:|
| `PUR` | 97 | 2 | ✅ |
| `LEI` | 65 | 1 | ✅ |
| `LOP` | 14 | 3 | ✅ |
| `SPI` | 13 | 4 · *«sin probar… hay que comprobarlo»* | 🟡 |
| `PIS` | 14 | **«no se usa»** | ⛔ |
| `SWO` | **0** | último · *«solo si ninguna otra cubre el pasaje»* | ✅ |

**Las cuatro primeras son las cuatro primeras de §4.bis, y `SWO` está fuera justo donde
§4.bis la deja.** Conviene decirlo porque durante dos días se leyó al revés: `D-9` llegó a
afirmar que *«el corpus se armó casi en el orden inverso al de su propio documento de
estrategia»*, y eso salía de citar **§4**, que es el orden *propuesto* y está derogado por
§4.bis. Corregido el 2026-08-10.

### ⛔ `PIS` dice «no se usa» y tiene 14 fragmentos · esta es la constancia que faltaba

**Entró el 2026-08-09 por un hueco concreto, no por descuido.** `N15` —derivadas de
exponenciales y logarítmicas— estaba **comprometido por el alcance** y tenía cero
fragmentos. En `LEI` el material es el capítulo 5, **que no está transcrito**; ninguna de
las otras cuatro obras transcritas lo cubría. `PIS` lo cubre entero en §8, §10 y §12.

**La regla de §4.bis que se aplicó fue la de `SWO`, no la de `PIS`:** *«solo si ninguna
otra cubre el pasaje»*. Se cumplía, y se verificó consultando el índice antes de trocear.

**Y el motivo por el que `PIS` estaba descartada resultó no aplicar a este ejemplar.** El
descarte se basó en *«OCR de Acrobat sobre edición de 1977 — inservible»*. La conversión
que se usó **conserva el número de página impreso** con marcas `(Página N)`, de modo que
la procedencia de sus 16 fragmentos no está estimada, y el verificador de matemática
aprobó 13 de los 16 —los otros tres quedaron `abstracto` o `pendiente`, que es la conducta
correcta—. **Dos de ellos, `F-179` y `F-180`, se retiraron después**, pero por alcance
—derivación logarítmica— y no por calidad de transcripción.

**Qué cambia en la tabla, entonces:** `PIS` deja de ser *«no se usa»* y pasa a **«solo
para `N15`, y solo mientras el capítulo 5 de `LEI` no esté transcrito»**. No se promueve a
fuente general: fuera de `N15` la regla anterior sigue en pie.

### 🟡 `SPI` entró con una condición que nadie cerró

§4.bis la deja en *«sin probar. Mismo tipo de fuente que `LEI`, así que debería comportarse
igual — **hay que comprobarlo**»*. Sus 13 fragmentos entraron el 2026-08-09 **sin que
quede constancia de esa comprobación**.

**No es una alarma:** su paginación sí se verificó contra el escaneo —el capítulo 10
empieza en la página impresa 227 y su archivo lo declara— y ninguno de sus fragmentos
salió inválido. Lo que falta es la comprobación **como tal**, sobre una muestra de páginas
y contra el original, que es lo que §4.bis pedía. Va a `PM-X01` con la muestra de
fragmentos, no antes.

### ✅ `SWO` · cerrada por `D-9` el 2026-08-10

**Se declaró obra consultada, no obra del corpus**, con el motivo de §4.bis: es el único
escaneo con OCR previo y esta misma sección lo llama *«el peor, y del modo más
peligroso»*. Su ficha vive ahora en [`FUENTES.md`](FUENTES.md) §Obras consultadas, fuera
del catálogo que `claves_de_obra()` lee. **La degradación que este documento escribió el
2026-08-06 es la que la decisión ejecuta**, así que §4.bis no cambia: se cumple.

---

## 5. Lo que este documento no resuelve

- **Las figuras.** Ninguna obra aporta sus gráficas en forma reutilizable, y `DD-05`
  exige descripción textual alternativa. Está sin decidir si las simulaciones se
  describen desde cero o se apoyan en las del libro.
- **El umbral de cita.** Cuánto texto de una obra puede reproducir un fragmento sin
  dejar de ser cita. `DD-15` acota el uso, no la extensión.
- ~~**Si `SWO` se usa,** hay que resolver la correspondencia entre hoja del PDF y página
  del libro.~~ **Cerrado dos veces:** la correspondencia se midió el 2026-08-05 —`página
  impresa = hoja − 17`, y no es doble página— y el 2026-08-10 `D-9` declaró que `SWO` no
  aporta corpus. Queda anotada en `FUENTES.md` §Obras consultadas por si alguna vez vuelve.

---

*Corpus · `DD-15` §Corpus · `DD-02` verificación al ingerir · IU Colegio Mayor del Cauca*
