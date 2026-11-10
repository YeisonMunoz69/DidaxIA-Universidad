# Formato del corpus · cómo pasa un libro a ser material del sistema

> **Para qué sirve este archivo.** Responde a *«tengo un libro convertido a Markdown, ¿y
> ahora qué?»*. Es independiente de la herramienta que hizo la conversión.
>
> **Fecha:** 2026-08-06 · **Basado en:** las cinco páginas convertidas ese día, no en teoría.

---

## 1. La pregunta que hay que responder primero

**No es «en trozos de cuántas páginas».** Es **qué recupera el sistema cuando un estudiante
pregunta.**

El sistema no lee libros: **recupera tres fragmentos** —`ADR-002` fija k=3— y los pone en
el contexto del generador. Cada fragmento llega **solo**, sin sus vecinos, sin el capítulo
que lo rodea y sin la página de al lado.

> ### El fragmento es lo que el sistema puede citar de una vez. Todo el formato se deriva de eso.

De ahí las tres propiedades que un fragmento necesita:

| Propiedad | Por qué |
|---|---|
| **Se entiende solo** | Llega sin contexto. Un fragmento que empieza con *«Por lo tanto»* no sirve |
| **Trata una sola cosa** | Su representación es **un vector**. Dos ideas en un fragmento dan un vector que no se parece a ninguna de las dos |
| **Sabe de dónde viene** | `DD-15`: sin procedencia el corpus no se puede depurar, solo borrar entero |

---

## 2. Por qué cortar por páginas es el criterio equivocado

**No es una opinión: se comprobó el 2026-08-06.**

La página 119 de Purcell contiene **tres cosas distintas**: el enunciado del teorema, su
lectura en palabras y un ejemplo resuelto. Y la motivación —*«¿para qué sirve esta
regla?»*— **está en la página 118**, que en un corte por páginas cae en otro archivo.

| Lo que pregunta el estudiante | Dónde está la respuesta |
|---|---|
| *«¿Para qué sirve la regla de la cadena?»* | Purcell **118** |
| *«¿Cómo se enuncia?»* | Purcell **119**, arriba |
| *«¿Cómo la aplico a `(2x²−4x+1)⁶⁰`?»* | Purcell **119**, abajo |

Un corte cada diez páginas metería las tres en el mismo fragmento y las tres competirían
por un solo vector. Un corte página a página separaría la motivación del enunciado.

> **La página es una unidad de imprenta, no de sentido.** Existe porque el papel se acaba.

---

## 3. El criterio que sí funciona · la unidad pedagógica

**Se corta donde el libro ya cortó.** Un texto de cálculo está escrito en unidades que
tienen nombre propio, y esas son las fronteras:

| Unidad | Ejemplo de las páginas convertidas |
|---|---|
| **Motivación** | *«tendríamos que multiplicar los 60 factores…»* · Purcell 118 |
| **Definición o teorema** | `teorema 2.4 (Regla de la cadena)` · López Erazo 86 |
| **Lectura en palabras** | *«la derivada de la función exterior evaluada en la interna…»* · Purcell 119 |
| **Ejemplo resuelto** | `EJEMPLO 1` con su desarrollo completo · Purcell 119 |
| **Observación o corolario** | `Observación 56`, la notación de Leibniz · López Erazo 86 |
| **Ejercicio con solución** | `EJERCICIO 2.17` · López Erazo |

**Y hay una ventaja práctica:** el conversor ya las detecta. MinerU produjo
`## 2.8.1 Teorema Regla de la cadena` como encabezado en Leithold, y
`teorema 2.4 (Regla de la cadena.)` reconocible en López Erazo. **Las fronteras vienen
marcadas; no hay que inventarlas.**

### Tamaño orientativo, no regla

| | |
|---|---|
| **Lo habitual** | Entre un párrafo y media página |
| **Demasiado corto** | Una fórmula sola, sin la frase que dice qué es |
| **Demasiado largo** | Si contiene dos cosas que un estudiante preguntaría por separado, **son dos fragmentos** |

> **La prueba que zanja las dudas:** léalo en voz alta imaginando que es la única cosa que
> el sistema va a poder decir. Si hace falta añadir *«esto viene de…»* para que se entienda,
> el corte está mal.

---

## 3.bis Si ya tiene el libro en Markdown · la regla de troceo

**Sí, se puede automatizar el troceo**, y con bastante fiabilidad, porque un texto de
cálculo marca sus propias fronteras. La regla es de cuatro pasos y ninguno es sutil:

### Paso 1 · Cortar en los encabezados

Todo `#`, `##` o `###` abre un fragmento nuevo. El conversor los produce: en Leithold salió
`## 2.8.1 Teorema Regla de la cadena` sin que nadie se lo pidiera.

### Paso 2 · Cortar también en los marcadores del libro

Muchas unidades no llevan encabezado sino una palabra en negrita o versalita al principio
del párrafo. Se corta **antes** de cualquiera de estas, en principio de línea:

```
Teorema        teorema        TEOREMA
Definición     definición     DEFINICIÓN
Corolario      Lema           Proposición
Ejemplo        EJEMPLO        EJEMPLO ILUSTRATIVO
Observación    Nota           Solución
Ejercicio      EJERCICIO      Demostración
```

**Sin acentos y sin distinguir mayúsculas**, porque en `LOP` el acento sale separado y
`Observaci´on` no coincide con `Observación`.

### Paso 3 · Dos reglas que evitan los cortes malos

| Regla | Por qué |
|---|---|
| **Nunca cortar dentro de `$$…$$`** | Media fórmula no es nada. Se cuentan los delimitadores y si hay un número impar antes del corte, se pospone |
| **Nunca cortar dentro de un bloque de código o una tabla** | Misma razón |

### Paso 4 · Reunir lo que quedó demasiado corto

Un fragmento de menos de unos **200 caracteres** casi siempre es una fórmula suelta o un
título huérfano. **Se pega al fragmento anterior**, que es el que le da sentido.

> **La prueba de que el paso 4 hace falta:** si se trocea la página 86 de López Erazo solo
> por marcadores, `El factor $h'(x)$ es llamado derivada interna` queda como fragmento
> propio. Aislado no dice nada; pegado al teorema, es la mitad de su significado.

### Qué queda para una persona, siempre

| | |
|---|---|
| **Los metadatos** | Nivel APOS, registro de Duval y concepción no se deducen del texto |
| **La página exacta** | El troceo automático pierde el número de página si el conversor no lo conservó |
| **El juicio sobre el corte** | La regla acierta la mayoría de las veces; **la mayoría no es todas** |

> **Con un libro troceado cada 100 páginas la regla funciona igual**, porque no depende del
> tamaño del archivo de entrada: depende de los marcadores, que están donde el autor los
> puso. Lo único que se pierde con archivos grandes es saber en qué página estaba cada
> fragmento, y eso **hay que conservarlo desde la conversión**, no reconstruirlo después.

### ⚠️ Lo que la regla no puede hacer

**No detecta que una fórmula esté mal.** Trocear `\frac{dy}{dy}` lo separa igual de bien
que `\frac{dy}{du}`. El troceo es un problema de estructura; la corrección de la matemática
es `DD-02` y va después, con el CAS.

---

## 3.ter Partir de una fuente que ya tenga LaTeX limpio

**Es mejor, sin discusión.** Se saltan tres de los seis pasos de §5 —convertir, detectar
fronteras y corregir defectos de OCR— y la matemática llega correcta de origen en vez de
reconstruida.

**Y hay una posibilidad concreta que conviene explorar antes de convertir nada más:**

> `LOP` —*Ejercicios y problemas de Cálculo I y II*, de Tulio Emiro López Erazo— **está
> generado con LaTeX**: el PDF lo declara en su productor, `MiKTeX pdfTeX`. Su autor está en
> el Departamento de Matemáticas de la Universidad del Cauca y el trabajo es de 2023.
>
> **El archivo `.tex` existe en alguna parte.** Pedirlo cuesta un correo y ahorraría todo
> el trabajo de reconstrucción para esa obra: matemática exacta, español correcto y las
> fronteras marcadas por los propios comandos de LaTeX.

**Pero no resuelve el corpus entero, por dos motivos:**

| | |
|---|---|
| **`LOP` no desarrolla teoría** | Su autor lo dice en la introducción: *«el trabajo no es de carácter teórico»*. Para «La explicación» de cada concepto siguen haciendo falta `PUR` o `LEI` |
| **Las fuentes limpias de fuera pueden no estar prescritas** | Existen textos abiertos con fuente LaTeX, pero **no están en la bibliografía del microcurrículo**, que es lo que hoy justifica el corpus sin depender del criterio del equipo. Usarlos exige argumentar otra cosa |

> **La conclusión honesta:** conseguir el `.tex` de `LOP` es la mejor mejora disponible y
> cuesta poco intentarlo. No sustituye a las demás obras — las complementa.

Ya está fijado por el esquema del código y **no se inventa aquí**: vive en
`OE3-Implementacion/codigo/dominio/puertos/corpus.py` y lo comprueban 24 pruebas.

```markdown
---
identificador: F-014
nivel_apos: proceso
registro_duval: algebraico
concepcion_asociada: M21
nodo_grafo: N08
procedencia:
  obra: LEI
  pagina: 164
  captura: ocr
---

**Teorema · Regla de la cadena.** Si la función $g$ es diferenciable en $x$ y la
función $f$ es diferenciable en $g(x)$, entonces la función compuesta $f \circ g$
es diferenciable en $x$, y

$$(f \circ g)'(x) = f'(g(x))\,g'(x)$$
```

| Campo | Qué poner |
|---|---|
| `identificador` | `F-###`, correlativo. **No se reutiliza** aunque se borre un fragmento |
| `nivel_apos` | `accion` · `proceso` · `objeto` · `esquema` |
| `registro_duval` | `algebraico` · `grafico` · `numerico` · `verbal` |
| `concepcion_asociada` | Del catálogo `M01`–`M24`, o vacío. **No se inventan identificadores** |
| `nodo_grafo` | El nodo al que responde |
| `procedencia.obra` | La clave de tres letras de `corpus/FUENTES.md` |
| `procedencia.pagina` | **La de la edición impresa**, no la hoja del PDF. Si no se conoce la exacta, la **primera** del rango — ver §4.ter |
| `procedencia.pagina_hasta` | **Solo si la página es aproximada**: la última del rango. Ausente significa que `pagina` es exacta |
| `procedencia.captura` | `nativa` · `mixta` · `ocr` · `manual` |

### Por qué un archivo por fragmento y no uno por capítulo

| | |
|---|---|
| **Se puede retirar uno** | `DD-15` contempla retirar el material de una obra. Borrar archivos es trivial; editar un archivo grande, no |
| **El historial dice algo** | Un cambio en un fragmento es un cambio en una idea, y se ve en el diff |
| **Las docentes revisan de a poco** | Un archivo de 400 líneas no se revisa; uno de 15, sí |
| **El cargador ya lo espera así** | `adaptadores/salientes/corpus/cargador.py` recorre `*.md` |

### Organización de la carpeta

```
contenido/corpus/
├── FUENTES.md                  ← la ficha de cada obra
├── ESTRATEGIA-DE-EXTRACCION.md ← qué hacer con cada una
├── _obras/                     ← los libros. NO se versionan
├── _obras-md/                  ← su transcripción a Markdown. NO se versiona
└── fragmentos/
    ├── f-001.md
    ├── f-002.md
    └── …
```

**Plana, sin subcarpetas por obra o por concepto.** La agrupación ya está en los metadatos,
que es donde el sistema la busca. Una jerarquía de carpetas sería una segunda clasificación
que puede desincronizarse de la primera.

---

## 4.ter Cuando la página no se conoce · `DD-21`

**Las obras no imprimen el número en todas sus páginas.** La primera transcripción completa,
recibida el 2026-08-06, llegó **sin número en diecinueve de sus veintiún archivos**, y no
por defecto de la transcripción sino porque el libro no lo trae.

`DD-21` admite entonces un **rango**, con una condición: **se declara como rango**.

```markdown
procedencia:
  obra: SPI
  pagina: 198          # exacta · no lleva `pagina_hasta`
  captura: manual
```

```markdown
procedencia:
  obra: SPI
  pagina: 198          # aproximada · el fragmento está entre la 198 y la 204
  pagina_hasta: 204
  captura: manual
```

> **Un dato aproximado presentado como exacto es peor que uno ausente**, porque el ausente
> se nota. Por eso no se guarda un número cualquiera del rango: se guardan los dos.

### Cómo se obtiene el rango

**Se anota por archivo al transcribir, y el fragmento lo hereda.** Anotarlo por fragmento
exigiría una precisión que la fuente no da; anotarlo por archivo es barato y cierto.

**Lo que se pierde, y hay que saberlo al redactar:** un pasaje cuya procedencia es un rango
**no se puede citar con página exacta** en el documento de grado. Se cita el capítulo o el
rango. El fragmento lleva escrito cuál es su caso precisamente para que quien redacte no
tenga que adivinarlo.

**Lo que NO se pierde:** la retirada selectiva de `DD-15`. Se puede retirar el material de
una obra, y dentro de ella el de un capítulo o un rango — que es lo que la decisión
necesita.

---

## 4.bis El paso intermedio · `_obras-md/`

**Decidido el 2026-08-06**, cuando se empezó a transcribir las obras a Markdown por
secciones del índice en lugar de convertir página a página.

Hasta entonces este documento declaraba dónde viven los **fragmentos** y no dónde vive el
**libro transcrito**, que es un artefacto nuevo: ni es una obra fuente ni es material que
el sistema use.

| | |
|---|---|
| **Dónde** | `contenido/corpus/_obras-md/` |
| **Qué contiene** | Un `.md` por sección del índice de cada obra, con su LaTeX ya puesto |
| **Nombre** | La clave de tres letras de `FUENTES.md` y la sección: `PUR-2.4-regla-cadena.md` |
| **¿Se versiona?** | **No.** `.gitignore` lo excluye |

> **Por qué no se versiona, que es lo único discutible.** Le aplica el mismo razonamiento
> que a `_obras/`: `DD-15` exige poder **retirar** el material, y lo que entra al historial
> de git sobrevive en todos los clones aunque se borre del árbol de trabajo. Un Markdown
> íntegro de Purcell es tanto reproducción de la obra como su PDF — **el cambio de formato
> no cambia de qué es copia**.

**Y tiene un costo que conviene no descubrir después:** estos archivos **no se comparten
por el repositorio**. Quien los necesite en otro equipo los recibe por fuera. Es el mismo
inconveniente que ya tiene `_obras/` y se acepta por el mismo motivo.

**Lo que sí se versiona de este paso** son los fragmentos que salen de él, con su
`procedencia` apuntando a la obra y a la página impresa. La transcripción es un medio; la
trazabilidad viaja en el fragmento, no en la carpeta.

> ⚠️ **Transcribir no es verificar.** Un archivo de `_obras-md/` no ha pasado por `DD-02`.
> El paso 5 de §5 sigue siendo obligatorio y ocurre **sobre el fragmento**, no sobre la
> transcripción.

---

## 5. De la página convertida al fragmento · seis pasos

```
   PDF ──► Markdown ──► trocear ──► corregir ──► anotar ──► verificar ──► corpus
        (1)          (2)         (3)          (4)         (5)          (6)
```

| | Paso | Quién |
|:--:|---|---|
| **1** | ~~Convertir la página con una herramienta~~ · **superado el 2026-08-07**: las cinco obras se transcribieron a mano y viven en `corpus/_obras-md/`. Lo que se usó está archivado en `Backups/2026-08-07-extraccion-automatica-superada/` | — |
| **2** | **Trocear por unidad pedagógica**, siguiendo los encabezados que el conversor detectó | Persona |
| **3** | **Corregir los defectos conocidos** de esa obra. Ver la tabla de §6 | Guion + persona |
| **4** | Anotar los metadatos, incluida la procedencia | Persona |
| **5** | **Verificar la matemática** — `DD-02`, obligatorio | Puerto simbólico |
| **6** | Cargar y comprobar que el cargador no protesta | `pytest` |

> ⚠️ **El paso 5 no es opcional ni se aplaza.** `DD-02` exige verificar al ingerir, y en
> `SWO` apareció `dy/dy` donde la página dice `dy/du` — una fórmula falsa con aspecto de
> correcta. Sin el paso 5 eso entra y nadie lo nota.

**Comprobación al terminar una tanda:**

```powershell
cd OE3-Implementacion\codigo
python -m pytest -q
```

---

## 6. Defectos conocidos por obra, al 2026-08-06

Medidos sobre cinco páginas. **Se actualiza cuando aparezcan más.**

| Obra | Defecto | ¿Automatizable? |
|---|---|---|
| `LOP` | Acento separado · `funci´on` → `función` | ✅ Corregir |
| `LEI` | `\vphantom{…}` con basura dentro | ✅ Corregir · no renderiza nada |
| `PUR` | Glifo `¿` por la prima, **dentro de recuadros** | ⚠️ **Solo detectar.** La fórmula se lee de la página |
| `SWO` | **Fórmula plausible y falsa** · `dy/dy` por `dy/du` | ❌ **Ni detectar.** No hay firma que la delate |

**La cuarta fija la política:** `SWO` solo se usa si ninguna otra obra cubre el pasaje, y
verificando fórmula por fórmula.

---

## 7. Cuánto libro se pasa al corpus · la pregunta que queda abierta

**Hoy el alcance está acotado:** dieciséis concepciones en
`conceptos/MAPA-M01-M24.md`, las cuatro unidades del microcurrículo, y `DD-13` que empieza
por tres conceptos y mide. Con seis fragmentos por concepto salen **unos cien fragmentos**,
que son decenas de páginas y no miles.

**Pero hay una tensión que conviene no dar por resuelta.** Si un estudiante pregunta algo
que está en el libro y el corpus no cubre, el sistema **no inventa** —`ADR-006` U2 lo pone
en *modo sin fuente*, con confianza reducida— pero tampoco ayuda.

| Opción | A favor | En contra |
|---|---|---|
| **Corpus acotado** · lo actual | Todo verificado por `DD-02`. Retirada sencilla. Recuperación limpia | Vacíos visibles para el estudiante |
| **Corpus amplio** | Menos vacíos | Multiplica la verificación de `DD-02`, mete material fuera de alcance —integrales, series— que **compite en la recuperación**, y amplía la superficie de `DD-15` |
| **Dos capas** · verificada y de consulta | Cubre sin ensuciar la capa citable | **No existe en la arquitectura.** Sería decisión nueva, con su ADR |

> ### ✅ Decidido el 2026-08-06 · `DD-22` adopta el **corpus amplio**
>
> Entra el cálculo diferencial completo de las obras transcritas. Integral, series y
> multivariable siguen fuera. **Lo de arriba se conserva sin reescribir** porque es el
> planteamiento que dio valor a la decisión, y porque la columna «en contra» sigue siendo
> cierta: la decisión no la anula, la asume.
>
> **Y trae una obligación que no es opcional:** `ADR-002` acota por nodo antes de buscar,
> así que **el grafo se amplía antes de indexar en volumen**. Un índice grande con un grafo
> de diecisiete nodos no es la configuración adoptada — es la que la revisión mide peor.
> Ver `DD-22` §Lo que obliga.
>
> **Sigue en pie medir la frecuencia del modo sin fuente** en el objetivo 4. Ya no es lo
> que decide, sino lo que dirá si se decidió bien.

### 7.bis · Qué significa «completo», que no es obvio · 2026-08-08

**`DD-22` y la tabla del alcance no dicen lo mismo, y al trocear hay que elegir.**
`DD-22` admite *«el cálculo diferencial completo»* y solo deja fuera integral, series y
multivariable. La tabla §3 de
[`01-Definicion-del-Alcance.md`](../../../../ERS-Objetivo1/1-ALCANCE-COMPROMETIDO/01-Definicion-del-Alcance.md)
excluye además **derivación implícita y logarítmica, puntos críticos, extremos locales,
concavidad y la conversión gráfica f↔f′**. Leídos al pie de la letra, el primero mete al
corpus lo que la segunda aparta.

> ### La regla, mientras los autores no decidan otra cosa: manda la tabla del alcance.

**Y el motivo no es que sea la más autorizada, sino que el error es reversible en un
sentido y no en el otro.** Si la regla resulta demasiado estrecha, ampliarla es escribir
fragmentos: trabajo aditivo, barato y sin efectos retroactivos. Si resulta demasiado
ancha, corregirla es **retirar** material ya indexado, con todo lo que `DD-15` dice de lo
difícil que es eso. Ante dos lecturas defendibles, se toma la que se puede deshacer.

Tres consecuencias prácticas, para no volver a discutirlo en cada tanda:

| | |
|---|---|
| **`inventario-de-cobertura.py` ya aplica esta regla** | Lee la columna «Excluido del compromiso» y aparta esos títulos antes de buscarles nodo. Elegir la otra lectura obligaría a cambiar el comprobador, no solo el criterio |
| **Un tema excluido no recibe nodo** | Y sin nodo no se indexa, por `DD-22`. Las dos reglas encajan en esta lectura y chocan en la otra |
| **Excluido no es prohibido** | Como dice `NODOS-CANDIDATOS.md` §4.bis: el proyecto **puede** cubrir de más, lo que no puede es prometerlo. Si un enunciado concreto está comprometido aunque su sección no lo esté, entra el enunciado y no la sección |

**El último caso ya se dio.** Purcell §2.7 es derivación implícita —excluida—, pero
contiene el teorema de la regla de la potencia para exponentes racionales, y «reglas de
derivación: potencia» está comprometido sin matices. Entró el enunciado con su ejemplo;
no entró la demostración, que es derivación implícita en acción.

### 7.ter · Los repasos de capítulo no entran · decidido el 2026-08-08

§3 admite **«ejercicio con solución»** como unidad pedagógica, y la duda era si los
repasos de final de capítulo —`PUR` §2.10, `LEI` `rev_cap1` a `rev_cap3`— cuentan. **No
entran**, y el motivo son las dos palabras del final: *con solución*.

Contado sobre `PUR` §2.10, pp. 147–150: **cero soluciones desarrolladas**. Son 34
afirmaciones de verdadero o falso y varios conjuntos de problemas cuyas respuestas están
al final del libro, fuera de la transcripción. Un fragmento hecho con eso sería un
enunciado suelto, y falla las dos propiedades que §1 le exige: no **se entiende solo**
—no dice qué enseña— y no deja **nada que `DD-02` pueda verificar**.

> **Y hay una razón más fuerte, que zanja el caso.** Buena parte de esas afirmaciones son
> **deliberadamente falsas**: la número 13 de `PUR` §2.10 dice *«la derivada de un
> producto siempre es el producto de las derivadas»*. Indexarla sin su respuesta metería
> **matemática falsa** en el corpus de recuperación, con la forma de una afirmación del
> libro. Es exactamente lo que `DD-02` existe para impedir.

**Lo que sí puede rescatarse de un repaso**, si alguna vez hace falta, es un ejercicio que
traiga su desarrollo completo. Entonces es una unidad como cualquier otra y entra por la
regla de §3, no por ésta.

---

## 8. Lo que NO se hace

| | Por qué |
|---|---|
| **Volcar un libro entero sin trocear** | Un archivo de 500 páginas es un vector inútil y `DD-02` no se puede aplicar a él |
| **Cortar cada N páginas** | Corta por donde se acabó el papel. Ver §2 |
| **Meter material fuera del alcance** | Integrales, series y multivariable **compiten en la recuperación** con lo que sí importa |
| **Inventar identificadores de concepción** | El catálogo `M01`–`M24` es cerrado. Si algo no encaja, se dice; no se fuerza |
| **Versionar las obras** | `.gitignore` excluye `_obras/`. `DD-15` exige poder retirarlas |
| **Copiar del texto extraído sin mirar la página** | En `LOP` las primas salen delante de su función: quien copie del extracto escribe la fórmula al revés |

---

## 9. Un ejemplo completo, de la página al fragmento

**Origen:** Leithold, *El Cálculo*, 7.ª ed., página impresa 164.

La conversión produjo, entre otras cosas, un encabezado y una fórmula:

```markdown
## 2.8.1 Teorema Regla de la cadena

Si la función g es diferenciable en x y la función f es diferenciable en g(x),
entonces la función compuesta $f \circ g$ es diferenciable en x, y

$$( f \circ g ) ^ { \prime } ( x ) = f ^ { \prime } ( g ( x ) ) \ : g ^ { \prime } ( x )\tag{7}$$
```

**Se trocea** en su unidad: el teorema es un fragmento, el ejemplo ilustrativo que sigue es
otro. **Se corrige** el espaciado y se retira el `\tag{7}`, que es numeración interna del
libro y no significa nada fuera de él. **Se anota** y **se verifica**. Queda así:

```markdown
---
identificador: F-014
nivel_apos: objeto
registro_duval: algebraico
concepcion_asociada: M21
nodo_grafo: N08
procedencia:
  obra: LEI
  pagina: 164
  captura: ocr
---

**Teorema · Regla de la cadena.** Si la función $g$ es diferenciable en $x$ y la
función $f$ es diferenciable en $g(x)$, entonces la función compuesta
$f \circ g$ es diferenciable en $x$, y

$$(f \circ g)'(x) = f'(g(x))\,g'(x)$$
```

**Qué cambió y por qué:**

| | |
|---|---|
| `\tag{7}` retirado | Es la numeración del libro. Fuera de él no señala nada |
| Espaciado normalizado | `f ^ { \prime } ( x )` → `f'(x)`. Mismo significado, legible |
| `\ :` → `\,` | El primero es un espacio raro del conversor |
| Se añadió **Teorema ·** al principio | El fragmento llega solo: tiene que decir qué es |
| `nivel_apos: objeto` | Es el enunciado general, no un procedimiento concreto |

> **Lo que NO cambió: la matemática.** `(f∘g)'(x) = f'(g(x))g'(x)` es lo que la página dice.
> Si al normalizar hubiera cambiado, sería un fragmento falso con aspecto de correcto.

---

## 10. Lo que este documento no resuelve

- **El corrector automático de §6 no está escrito.** Ningún fragmento nuevo debería entrar
  antes de que exista.
- **Los seis fragmentos de `C-M21` no están enlazados a su concepto.** El grafo tiene el
  nodo, el corpus tiene el material, y nada los une todavía.
- **No se ha medido cuánto cuesta trocear** una página convertida. Se sabe lo que cuesta
  transcribir a mano —seis fragmentos, 21 expresiones— pero no partiendo de Markdown.
- **La tensión de §7** sigue abierta y no debería cerrarse sin el dato del objetivo 4.

---

*Corpus · `DD-02` · `DD-13` · `DD-15` · IU Colegio Mayor del Cauca*
