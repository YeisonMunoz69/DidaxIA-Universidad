# Fuentes del corpus

> ⚠️ **Antes de modificar nada, lea [`../../../../ANTES-DE-MODIFICAR.md`](../../../../ANTES-DE-MODIFICAR.md).**

| | |
|---|---|
| **Qué es** | La ficha de cada obra de la que sale un fragmento del corpus |
| **Decisión que lo exige** | [`DD-15`](../../../04-Decisiones-de-Detalle.md) §Corpus · uso autorizado y acotado |
| **Estado** | 🟢 2026-08-19 · **cinco obras aportan corpus y las cinco están troceadas** · **271 fragmentos escritos, 248 indexados**: al lote de `PM-C07` —6 de `C-M21`, `PUR` capítulo 2 (§2.1–§2.9), `LEI` (§1.2, el capítulo 2 entero, §3.3 y §3.10), `PIS` (§8, §10 y §12 — el logaritmo y la exponencial), **`SPI` (capítulo 10, «Derivación»)** y **`LOP` (§2.1 y §2.6)**— se suman los **68 de `PM-C21`**, del 2026-08-19: límites y continuidad (`PUR` §1.1–§1.6, `LEI` §1.5–§1.10) y el tercer corte (`LEI` §2.9, §2.10, §3.1, §3.4, §3.5; `PIS` cap. IV; `LOP` cap. 3) |
| **Una obra queda fuera, y no por olvido** | **`SWO` · Swokowski · cero fragmentos, por decisión `D-9` del 2026-08-10.** Es **obra consultada, no obra del corpus**: su ficha está abajo, fuera del catálogo, y ninguna clave de fragmento puede citarla |
| **Fecha** | 2026-09-05 |

---

## Por qué existe este archivo

`DD-15` inició el uso de este material para las pruebas del objetivo 4. La
decisión institucional registrada por el equipo el **2026-09-05** amplía su
alcance al piloto autenticado y a la presentación del trabajo de grado: se
pueden consultar fragmentos, transcripciones y ejemplares dentro de DidaxIA,
sin convertirlos en una biblioteca pública o anónima. Cada fragmento conserva
su procedencia porque *«un corpus sin procedencia no se puede depurar, solo
borrar entero»*.

Este archivo es la mitad estable de esa procedencia. El fragmento cita una **clave de
obra** —`PUR`, `LOP`, `SWO`…— y una página; la ficha de qué es esa clave vive aquí y no
se repite en cada fragmento. Es la misma regla que el resto del proyecto aplica a los
catálogos: el dato vive en un sitio y los demás lo referencian.

## Copias institucionales versionadas

Desde la decisión del 2026-09-05 se versionan únicamente las copias
normalizadas y catalogadas de [`_obras/`](_obras/) y
[`_obras-md/`](_obras-md/). Los originales de trabajo, revisiones y archivos
auxiliares permanecen ignorados. Las rutas que sirven estas copias exigen una
sesión institucional autenticada y vuelven a comprobar el permiso de este
archivo en cada petición.

La trazabilidad en Git permite que el despliegue reciba exactamente el mismo
material probado. Una retirada futura se ejecuta cambiando el permiso a
`retirado`, bloqueando el canal en el backend y registrando la decisión; no se
presenta el borrado del último commit como si eliminara copias históricas.

---

## Las obras

Ocho obras distintas en diez archivos. Las claves son las que citarán los fragmentos.

Los datos editoriales se verificaron contra catálogos en línea el 2026-08-05; las
comprobaciones internas —páginas del archivo, capa de texto, correspondencia de
paginación— salen de muestrear los archivos.

> ### ⚙️ Esta lista la lee un programa, y por eso su forma importa
>
> `claves_de_obra()` en `adaptadores/salientes/corpus/cargador.py` saca el catálogo de
> obras **de los encabezados `### \`XXX\`` de esta sección**, con la expresión
> `^###\s+\`([A-Z]{3})\``. Lo que aparece ahí es lo que un fragmento puede citar en su
> campo `obra:`, y lo que el arnés de recuperación cuenta como material que debería
> estar en el índice.
>
> **Añadir una ficha aquí es añadir una obra al corpus**, y quitarla de aquí es sacarla.
> Una obra que se consulta pero no aporta fragmentos va abajo, en §Obras consultadas,
> con encabezado `####` para que el catálogo no la recoja. **`SWO` está ahí desde
> `D-9`.**

### `LOP` · López Erazo

| | |
|---|---|
| **Obra** | López Erazo, Tulio Emiro. *Ejercicios y problemas de Cálculo I y Cálculo II* |
| **Procedencia** | Departamento de Matemáticas, **Universidad del Cauca**. 15 de enero de 2023 |
| **Archivo** | PDF generado con LaTeX (MiKTeX pdfTeX), 571 páginas |
| **Paginación** | La del archivo coincide con la de la obra |
| **Referencia institucional** | [Universidad del Cauca](https://www.unicauca.edu.co/) · la página identifica a la institución, pero **no es un lector de la obra ni prueba permiso de publicación** |

Es la obra más reciente del lote y la única sin ISBN ni editorial: es material docente.
Su autor declara en la introducción que *«el trabajo no es de carácter teórico»* — son
unos 800 ejercicios y problemas.

> ⚠️ **No es de la institución de este proyecto.** La Universidad del Cauca y la
> Institución Universitaria Colegio Mayor del Cauca son entidades distintas, ambas en
> Popayán. `LOP` viene de la primera; el microcurrículo que ordena el mapa de
> concepciones, de la segunda.

### `PUR` · Purcell, Varberg y Rigdon

| | |
|---|---|
| **Obra** | Purcell, Edwin J.; Varberg, Dale; Rigdon, Steven E. *Cálculo diferencial e integral* |
| **Edición** | 9.ª · adaptación autorizada al español de *Calculus, 9e* |
| **Editorial** | Pearson Educación / Prentice Hall, 2007 |
| **ISBN** | 978-970-26-0989-6 |
| **Archivo** | PDF editorial con capa de texto nativa, 519 páginas |
| **Referencia externa por verificar** | [Open Library · ficha de *Calculus*](https://openlibrary.org/books/OL366710M/Calculus) · confirmar que edición, autores y paginación correspondan antes de enlazarla desde un fragmento |

⚠️ **Origen probable del archivo:** el nombre `[Purcell,Varberg,Rigdon]Calculo.pdf`
coincide **carácter por carácter** con la copia que el Centro de Investigación en
Matemáticas de México publica en su biblioteca abierta para bachillerato. Es un
repositorio institucional, no una biblioteca en la sombra.

### `LEI` · Leithold

| | |
|---|---|
| **Obra** | Leithold, Louis. *El Cálculo* |
| **Edición** | 7.ª (*EC7*) · Oxford University Press – Harla México, 1998 |
| **ISBN** | 978-970-613-182-9 · 1 360 páginas impresas |
| **Archivo** | PDF escaneado a ~300 ppi, **sin capa de texto**, 1 380 páginas |
| **Referencias externas por verificar** | [Internet Archive · *El Cálculo*](https://archive.org/details/leithold-el-calculo-espanol-7a.-ed.) · [Open Library · *The Calculus 7*](https://openlibrary.org/books/OL8692737M/The_Calculus_7) · su disponibilidad no prueba por sí sola autorización del titular |

### `SPI` · Spivak

| | |
|---|---|
| **Obra** | Spivak, Michael. *Calculus · Cálculo Infinitesimal* |
| **Edición** | 2.ª en español · Editorial Reverté · 944 páginas impresas |
| **ISBN** | 978-84-291-5136-7 |
| **Archivo** | PDF escaneado a 400 ppi bitonal, **sin capa de texto**, 920 páginas |
| **Procedencia del archivo** | ⚠️ ver la nota de abajo |
| **Referencias externas** | [Editorial Reverté · ficha de *Calculus*](https://www.reverte.com/libro/calculus_91544/) · [Open Library · ficha bibliográfica](https://openlibrary.org/books/OL24361545M/Calculus) · la ficha editorial es referencia oficial, no lector del texto completo |

### `PIS` · Piskunov

| | |
|---|---|
| **Obra** | Piskunov, N. *Cálculo Diferencial e Integral, Tomo I* |
| **Edición** | Editorial Mir, Moscú, 1977 · traducción del ruso de K. Medkov |
| **Archivo** | PDF escaneado con OCR de Acrobat, 530 páginas · más dos `.epub` |
| **Procedencia del archivo** | Prefijo `UNICAUCA-`. El nombre del `.epub` reproduce el identificador de un ejemplar de Internet Archive |
| **Referencia externa por verificar** | [Internet Archive · Tomo I (Editorial Mir, 1977)](https://archive.org/details/n.-piskunov-calculo-diferencial-e-integral-tomo-i-editorial-mir-1977esp) · la carga de un tercero no demuestra autorización del titular |

---

## Obras consultadas · fuera del catálogo del corpus

**Están aquí porque se leyeron y se descartaron con motivo escrito, no porque se
olvidaran.** Sus encabezados van con `####` a propósito: `claves_de_obra()` no las
recoge, de modo que ningún fragmento puede citarlas y el arnés no las cuenta como
material que falta.

#### `SWO` · Swokowski · ⛔ **no aporta corpus · `D-9`, 2026-08-10**

| | |
|---|---|
| **Obra** | Swokowski, Earl W. *Cálculo con Geometría Analítica* |
| **Edición** | 2.ª · Grupo Editorial Iberoamérica, México, 1989 |
| **ISBN** | 968-7270-43-8 |
| **Archivo** | PDF escaneado con OCR de Internet Archive, **244 hojas** |
| **Procedencia del archivo** | Prefijo `Unicauca-` |
| **Estado** | **Obra consultada.** Prescrita por el microcurrículo · **cero fragmentos** |
| **Referencias externas por verificar** | [Internet Archive · *Cálculo con geometría analítica*](https://archive.org/details/calculo-con-geometria-analitica-earl-swokowsk) · [Open Library · ficha bibliográfica](https://openlibrary.org/books/OL8693892M/Calculus_with_analytic_geometry) |

**Por qué queda fuera, y el motivo está medido.**
[`ESTRATEGIA-DE-EXTRACCION.md`](ESTRATEGIA-DE-EXTRACCION.md) §4.bis —*«Orden vigente ·
medido sobre cinco páginas el 2026-08-06»*— la degrada a *«solo si ninguna otra cubre el
pasaje, y verificando fórmula por fórmula contra la página»*, porque es el **único escaneo
con OCR previo** del proyecto y ese es el caso que la medición identificó como *«el peor, y
del modo más peligroso»*: produce texto plausible y falso, que **no pide revisión**.

**Lo que su escaneo cubría, y por qué se pudo prescindir.** La obra impresa tiene 1 168
páginas; el archivo llega hasta la **página 227**, final del capítulo 4: funciones,
límites, la derivada y valores extremos. De eso, límite y continuidad son **prerrequisito
declarativo** y valores extremos está **excluido** por la tabla del alcance. Lo que
quedaba —la derivada— ya lo cubren `PUR` y `LEI`, que §4.bis pone en los dos primeros
puestos.

> **Correspondencia de paginación, por si alguna vez vuelve: `página impresa = hoja del
> PDF − 17`.** Comprobado en cinco puntos (hoja 80 → p. 63 · 120 → 103 · 230 → 214 ·
> 243 → 227).

**Cómo se dice al sustentar.** *«El microcurrículo prescribe cuatro obras; tres aportan
material al corpus. `SWO` se consultó y quedó fuera porque su único ejemplar disponible
es un escaneo con OCR previo, que la medición del 2026-08-06 identificó como la fuente de
error más difícil de detectar.»*

**Si se decidiera revertir**, basta con devolver esta ficha a §Las obras con encabezado
`###` y actualizar `test_cargador_corpus.py`. Nada más depende de ella.

---

## Los cuatro archivos que no son obras nuevas

| Archivo | Qué es en realidad |
|---|---|
| `N. Piskunov …esp.epub` y `… (1).epub` | **El mismo archivo dos veces.** `md5 = e959340f…` en ambos. Uno sobra |
| `Cálculo I.epub` | **No es una obra distinta: es `SPI` otra vez**, en un volcado de OCR degradado. El texto interno son los problemas de Spivak |
| `MICROCURRÍCULO_…docx` | **No es corpus.** Es el microcurrículo de Cálculo Diferencial de Ingeniería Multimedia. Ver abajo |

---

## ★ Cuatro de estas obras son bibliografía oficial del curso

Es el hallazgo con más valor para la sustentación, y salió de leer el microcurrículo
entero. Su sección **Bibliografía** prescribe, entre otras:

| En el microcurrículo | Lo que hay en `_obras/` |
|---|---|
| Leithold, L. 1973. *El Cálculo con Geometría Analítica*. Harla | `LEI`, 7.ª ed. 1998 |
| Piskunov, N. 1982. *Cálculo Diferencial e Integral*. Montaner y Simón | `PIS`, Mir 1977 |
| Purcell, E. J. y D. Varberg. 1987. *Cálculo con Geometría Analítica*. Prentice Hall | `PUR`, 9.ª ed. 2007, con Rigdon |
| Swokowski, E. W. 1982. *Cálculo con Geometría Analítica*. Iberoamericana | `SWO`, 2.ª ed. 1989 |

**Las ediciones no coinciden, los autores y las obras sí.** El corpus no se arma con
material elegido por conveniencia: se arma con los textos que el propio programa del
curso prescribe, en ediciones distintas de las citadas.

> Eso da al corpus una justificación que no depende del criterio del equipo, y conviene
> escribirla así en el documento de grado. También acota qué se puede añadir después sin
> tener que argumentarlo de nuevo.

El microcurrículo cita además Apostol, Ayres (Schaum), Larson, Stewart y Zill, que **no
están en `_obras/`**. Y no cita a Spivak ni a López Erazo, que sí están.

### Decidido el 2026-08-09 · `SPI` y `LOP` se quedan, con otra justificación

> **Que una obra no prescrita entre al corpus es una decisión, y se toma por escrito en
> vez de darse por hecha.**

`SPI` aporta 21 fragmentos —el capítulo 10, «Derivación»— y `LOP` aporta §2.1 y §2.6.
**Ninguna de las dos está en la bibliografía del microcurrículo.** Se quedan, y el motivo
**no es el mismo** que el de las otras cuatro:

| | Cómo se justifica |
|---|---|
| `LEI` `PIS` `PUR` `SWO` | *«Las prescribe el programa del curso.»* La justificación no depende del criterio del equipo |
| `LOP` | *«Es del Departamento de Matemáticas de la Universidad del Cauca»*, y consta en la portada. Material docente de la propia institución |
| `SPI` | *«La aportó la universidad»*, confirmado por los autores, **y es citable por su ISBN**. Spivak es texto canónico de cálculo, no una fuente de conveniencia |

**Al sustentar se dicen distinto, y esa es la mitad del valor de escribirlo.** Presentar
las seis bajo una sola frase —*«son las obras del curso»*— sería inexacto, y basta que
alguien abra la bibliografía del microcurrículo para verlo.

> **Lo que esto NO autoriza:** añadir obras por conveniencia. La regla sigue siendo que
> una obra entra si el programa la prescribe **o** si la institución la aportó y queda
> escrito aquí cuál de las dos cosas es. Cualquier tercera vía se decide antes, no
> después de trocear.

---

### El microcurrículo, que cumple otra función

`MICROCURRÍCULO_CALCULO_DIFERENCIAL_ING_MULTIMEDIA_MIERCOLES_10-1.docx` no aporta
fragmentos. Es el **contrato curricular** del curso: qué se enseña, en qué orden, con
cuántas horas y bajo qué competencias.

Es de la **Institución Universitaria Colegio Mayor del Cauca** —Ingeniería Multimedia,
docente Edith Janeth Potosí Estrada— o sea de la institución de este proyecto. Su
contenido sintético son cuatro unidades: funciones · límite y continuidad · la derivada ·
aplicaciones de la derivada.

> 🐛 **Corregido el 2026-08-13.** El párrafo anterior decía *«el contrato curricular de la
> **Universidad del Cauca**»* y el siguiente, *«es de la **Institución Universitaria
> Colegio Mayor del Cauca**»* — **dos instituciones distintas para el mismo documento, en
> párrafos consecutivos**. La correcta es la segunda: el microcurrículo es del Colegio
> Mayor, que es la institución de este proyecto, y así lo cita también
> `conceptos/MAPA-M01-M24.md`. La confusión probable viene de que **`LOP` sí es de la
> Universidad del Cauca**, y las dos entidades están en Popayán. **Importa porque el
> microcurrículo es lo que fija el orden del mapa de concepciones**: atribuirlo a otra
> institución invalidaría ese criterio en la sustentación.

Su uso es fijar el **orden** del mapa de concepciones y dar contexto curricular a `S12`.
Se conserva en `_obras/` por comodidad, pero conviene no confundirlo con material del que
se extraiga contenido.

> Hubo un segundo programa, `MAT102.pdf`, de otra universidad. Se usó para contrastar y
> **se retiró**. No entra en el mapa.

---

## ✅ La procedencia de `SPI`, resuelta el 2026-08-06

> **El ejemplar lo entregó la universidad**, como los demás. La duda queda cerrada por
> declaración de los autores.

**Lo que la levantó, y se conserva escrito porque el razonamiento sigue valiendo:** el
archivo trae `libgen.li` en su nombre, una cadena que identifica una biblioteca en la
sombra, y eso **declaraba un origen distinto del que `DD-15` supone**. La duda era sobre el
**ejemplar**, no sobre la obra —que está identificada por su ISBN y es citable sin
reservas—, y esa distinción es la que hace que la pregunta tuviera sentido y no fuera una
sospecha.

> ⚠️ **Conviene renombrar el archivo.** El nombre seguirá levantando la misma duda a quien
> lo mire dentro de un año, y la respuesta ya no estará en la cabeza de nadie. Un nombre
> que contradice la procedencia registrada es una desincronización como cualquier otra.

**Y una precisión que no cambia con esto:** la sección de arriba dice que el microcurrículo
prescribe Leithold, Piskunov, Purcell y Swokowski, y **no cita a Spivak**. Sigue siendo
cierto y no está reñido con lo anterior: que la universidad entregue una obra no implica que
el programa la prescriba. **Son dos justificaciones distintas y las dos son válidas** —
`DD-15` autoriza el material aportado por las docentes—, pero al sustentar conviene no
mezclarlas: de las cuatro se dice *«las prescribe el programa»*; de esta, *«la aportó la
universidad»*.

**La distinción que importa** no es entre obra legítima e ilegítima, sino entre **la obra
y el ejemplar**. La obra está identificada por su ISBN y es citable sin reservas. Lo que
varía es de qué copia digital salió el texto, y eso es lo que esta tabla registra.

| Clave | Origen del ejemplar digital | Estado |
|---|---|:--:|
| `LOP` | Departamento de Matemáticas de la Universidad del Cauca | 🟢 consta en la portada |
| `SWO` · `PIS` | Biblioteca de la Universidad del Cauca, según el prefijo del nombre | 🟡 se deduce del nombre |
| `PUR` | Repositorio abierto del CIMAT, según el nombre del archivo | 🟡 coincidencia exacta del nombre |
| `LEI` | Por confirmar | ⬜ |
| `SPI` | **Lo entregó la Universidad del Cauca**, confirmado por los autores el 2026-08-06 | 🟢 |

> ### El aviso de `SPI` se retira el 2026-08-09
>
> Hasta hoy esta tabla decía *«por aclarar — el nombre apunta a una biblioteca en la
> sombra»* y añadía *«conviene resolverla antes de que se use»*. **Las dos frases ya eran
> falsas:** la procedencia se aclaró el 2026-08-06 —§«La procedencia de `SPI`, resuelta»,
> más abajo— y `SPI` lleva 21 fragmentos dentro del corpus desde el 2026-08-09. El aviso
> se quedó por descuido y `PM-C06.ter` lo daba por retirado sin estarlo.
>
> **`LEI` sí sigue por confirmar**, y ésa no se toca.

---

## Cómo se cita en un fragmento

La procedencia de un fragmento se escribe con la clave, no con el título:

```yaml
procedencia:
  obra: PUR          # clave de la tabla de arriba
  pagina: 119        # página de la EDICIÓN, no del archivo PDF
  captura: mixta     # cómo se obtuvo: ver ESTRATEGIA-DE-EXTRACCION.md
```

**La página es la de la edición impresa**, la que un lector encontraría, y no el índice
del archivo. En `LOP` y `PUR` coinciden. En `SWO` **difieren en 17**, comprobado en cinco
puntos. En `SPI` y `LEI` difieren por las páginas preliminares y falta medir el desfase.

---

## Lo que falta

- [x] **Aclarar la procedencia del ejemplar de `SPI`** — cerrado el 2026-08-06 y **la tabla
      corregida el 2026-08-09**: lo entregó la universidad. Queda una tarea de forma,
      renombrar el archivo, porque su nombre volverá a levantar la misma duda
- [ ] Confirmar de dónde salió el ejemplar de `LEI`
- [x] Medir el desfase de paginación de `LEI`: **+22**, comprobado en las hojas
      24, 253 y 309 contra las páginas impresas 2, 231 y 287
- [x] **`SPI` no tiene desfase, comprobado el 2026-08-09** contra el escaneo: el capítulo
      10 empieza en la página impresa **227** y su archivo declara *«[Pagina 227 a 234 del
      libro]»*. Coinciden
- [x] **`LOP` tampoco**, y ya constaba en su ficha. Sus fragmentos citan el rango de
      sección que da el índice de la obra —§2.1 pp. 84–93, §2.6 pp. 127–135— y las páginas
      exactas que dan las notas de figura. **Ninguna está estimada**
- [x] **`PIS` no tiene desfase que medir, comprobado el 2026-08-09.** Su conversión
      conserva el número impreso: cada archivo se abre con su rango —`8.md` dice
      *«[Pagina 88 a 99 del libro]»*— y dentro lleva una marca `(Página N)` al cerrar
      cada página. Donde el archivo **no** las lleva —`7.md`, que es el de §8— la página
      se leyó del escaneo: §8 empieza en la **84** y termina en la **85**. Las páginas de
      los 16 fragmentos de `PIS` salen de ahí, **ninguna está estimada**
- [ ] Decidir si se retira el `.epub` duplicado de `PIS` y el volcado `Cálculo I.epub`
- [ ] Registrar la fecha en que cada obra se recibió y de qué docente

---

## Puerta de publicación institucional · decisiones D0 y 2026-09-05

El equipo desea aportar a la comunidad una biblioteca navegable con la obra,
su conversión Markdown y los fragmentos que usa DidaxIa. **Ese objetivo queda
registrado, pero no equivale todavía a autorización para redistribuir.** Que un
PDF pueda descargarse de un sitio o consultarse en una biblioteca virtual no
demuestra por sí solo que se pueda republicar completo en `didaxia.pro`.

### Estrategia de producto adoptada, condicionada a auditoría de citas

> [!NOTE]
> El equipo adopta como dirección de producto **renderizar únicamente fragmentos
> pedagógicos breves y necesarios**, con atribución verificable, y no publicar
> los PDFs ni los Markdown continuos protegidos. Esta dirección reduce el riesgo
> de redistribución, pero no convierte automáticamente los 271 fragmentos en
> citas lícitas: cada uno y el conjunto acumulado por obra deben superar la
> revisión descrita abajo.

1. **Visor pedagógico condicionado:** un fragmento (`F-001.md`, etc.) solo se
   habilita cuando identifica autor, título, edición y página; contiene lo
   necesario para la explicación; y no sustituye una parte sustancial de la
   obra.
2. **Control acumulado:** además de revisar cada fragmento, se mide por obra la
   cantidad, continuidad y cobertura conjunta. No se ofrecerán navegación
   masiva, exportación ni secuencias que permitan reconstruir capítulos o el
   libro a partir de fragmentos aislados.
3. **Referencia externa:** la caja de atribución puede abrir una ficha oficial
   o un lector externo en otra pestaña (`target="_blank"
   rel="noopener noreferrer"`). Antes de publicarlo se comprueba edición,
   estabilidad y procedencia. Enlazar un ejemplar subido por un tercero no
   equivale a certificar su licencia.
4. **Material interno no expuesto:** los PDF (`_obras/`) y capítulos completos
   transcritos (`_obras-md/`) permanecen fuera de la superficie pública como
   apoyo para extracción y verificación matemática.
5. **Regla de fallo seguro:** ante duda de atribución, extensión, continuidad o
   licencia, el fragmento queda deshabilitado hasta obtener revisión o permiso.

Esta política se fundamenta en los artículos 31 y 32 de la Ley 23 de 1982 y en
los artículos 21 y 22 de la Decisión Andina 351: exige autor y título, medida
justificada por el fin educativo y ausencia de una reproducción sustancial que
perjudique la explotación normal. Es un criterio operativo del equipo, no una
declaración de cumplimiento jurídico automático ni asesoría legal.

### Cómo se diligencia realmente

Este Markdown **no es un formulario**: la vista previa del editor o de GitHub es de
solo lectura y, además, la sección `Las obras` tiene encabezados que consume el
código. El instrumento editable es
[`Registro-Publicacion-Fuentes.xlsx`](../../../../outputs/fuentes-publicacion/Registro-Publicacion-Fuentes.xlsx).

1. Abrir el libro en Excel o LibreOffice y leer primero la hoja `Instrucciones`.
2. Completar una obra por fila en `Registro`; las decisiones y estados se eligen en
   listas desplegables para no introducir sinónimos ambiguos.
3. No pegar cartas, firmas, correos privados ni datos personales. En la columna de
   evidencia privada se escribe únicamente un identificador o una ruta controlada.
4. Yeison y Fabián revisan juntos la evidencia y consignan decisión, responsable y
   fecha. Una celda vacía o el estado `pendiente` **no autoriza** ninguna publicación.
5. Cuando una decisión quede aprobada, se sincroniza la tabla de estado de este
   archivo en el mismo cambio. No se renombra ninguna clave ni se altera un encabezado
   `### \`XXX\`` para registrar permisos.

El libro separa tres salidas porque una autorización puede cubrir unas y no otras:
PDF completo, Markdown continuo y fragmentos citados. Su hoja `Resumen` se calcula a
partir del registro y permite comprobar cuántas obras siguen bloqueadas.

Antes de habilitar el PDF completo o una conversión Markdown sustitutiva de la
obra, cada ficha debe añadir y demostrar estos campos:

| Campo | Evidencia mínima |
|---|---|
| Titular o entidad que autoriza | Nombre verificable del titular, editorial, autor o repositorio con facultad para licenciar |
| Tipo de autorización | Licencia abierta, dominio público, permiso escrito o convenio institucional |
| Alcance | Reproducción, transformación a Markdown y comunicación pública por Internet |
| Territorio y plazo | Cobertura aplicable y fecha de vencimiento, si existe |
| Atribución exigida | Texto, enlace, aviso de licencia y cualquier restricción de uso |
| Evidencia conservada | URL estable, captura fechada, carta, correo institucional o documento firmado |
| Decisión del equipo | `publicable`, `solo uso interno`, `solo cita/fracción` o `retirar` |

### Estado y estrategia de publicación por obra

**Decisión institucional del 2026-09-05.** El equipo registra que la
Institución requiere la lectura de los fragmentos Markdown y de los PDF dentro
de DidaxIA para el piloto y la sustentación del trabajo de grado. El alcance es
**uso institucional autenticado**: el backend exige sesión verificada incluso
para los metadatos de esta biblioteca. No se habilita una ruta pública o
anónima, ni se permite reconstruir una ruta de disco desde el cliente.

| Clave | PDF completo público | Markdown continuo público | Fragmentos (`fragmentos/`) | Referencia o lector externo |
|---|:---:|:---:|:---:|---|
| `LOP` | 🟢 autorizado · institucional | 🟢 autorizado · institucional | 🟢 autorizado · institucional | referencia institucional; lector interno de DidaxIA |
| `PUR` | 🟢 autorizado · institucional | 🟢 autorizado · institucional | 🟢 autorizado · institucional | [Open Library · ficha](https://openlibrary.org/books/OL366710M/Calculus) · lector interno de DidaxIA |
| `LEI` | 🟢 autorizado · institucional | 🟢 autorizado · institucional | 🟢 autorizado · institucional | [Internet Archive](https://archive.org/details/leithold-el-calculo-espanol-7a.-ed.) · [Open Library](https://openlibrary.org/books/OL8692737M/The_Calculus_7) · lector interno de DidaxIA |
| `SPI` | 🟢 autorizado · institucional | 🟢 autorizado · institucional | 🟢 autorizado · institucional | [Editorial Reverté](https://www.reverte.com/libro/calculus_91544/) · [Open Library](https://openlibrary.org/books/OL24361545M/Calculus) · lector interno de DidaxIA |
| `PIS` | 🟢 autorizado · institucional | 🟢 autorizado · institucional | 🟢 autorizado · institucional | [Internet Archive](https://archive.org/details/n.-piskunov-calculo-diferencial-e-integral-tomo-i-editorial-mir-1977esp) · lector interno de DidaxIA; sin PDF completo en el lote |
| `SWO` | ⛔ fuera del corpus | ⛔ fuera del corpus | ⛔ no aporta fragmentos | referencia externa por verificar |

`Autorizado · institucional` habilita el canal únicamente detrás de la sesión
verificada del piloto. Los metadatos, fragmentos y obras obedecen la misma
frontera de autenticación. `SWO` permanece fuera porque no aporta fragmentos y
la decisión `D-9` no fue revertida.

La evidencia se guarda fuera del árbol público si contiene firmas, correos u
otros datos personales. Este archivo conserva solo su identificador, fecha,
alcance y decisión.

---

## Correcciones de este archivo

**2026-08-10 · «ninguna queda fuera» era falso, y lo desmentía este mismo archivo.** La
casilla de estado decía *«las cinco obras transcritas Y troceadas, ninguna queda fuera»*
mientras el catálogo declaraba **seis** y `SWO` tenía su ficha completa doce líneas más
abajo. **Es exactamente el defecto que `PM-V09` acababa de arreglar en el arnés** —un dato
de estado escrito a mano en vez de contado— y estaba en el archivo del que el arnés saca
la cuenta. Lo destapó la revisión de Cowork del 2026-08-10 comparando la casilla con la
salida de `claves_de_obra()`. Corregido junto con `D-9`: `SWO` pasó a §Obras consultadas,
el catálogo devuelve **cinco** claves, y la casilla dice qué queda fuera y por qué.

**2026-08-05 · la paginación de `SWO`.** La primera versión afirmaba que el escaneo
llevaba **dos páginas por hoja**. Era falso: se dedujo del tamaño de página del PDF
—1 030 × 1 358 puntos— sin comprobarlo. Al verificar los encabezados de cinco hojas
resultó ser **una página por hoja con desfase de 17**, y además se descubrió que el
escaneo termina en la página 227 de 1 168. Ninguna de las dos cosas se sabía al escribir
la primera versión.

**2026-08-05 · la institución de `LOP`.** La primera versión la llamaba *«la única obra
del lote de la propia institución»*. Es falso y confunde dos entidades: `LOP` es de la
**Universidad del Cauca** y este proyecto es de la **Institución Universitaria Colegio
Mayor del Cauca**. Se detectó al leer el microcurrículo, cuyo correo docente es
`@unimayor.edu.co`. El error venía de leer *«Cauca»* en las dos partes y no distinguirlas.

---

*Corpus · `DD-15` §Corpus · IU Colegio Mayor del Cauca*
