# Corpus pedagógico

> **Esto no es código.** Es autoría pedagógica, y está separado a propósito
> (`02-Estructura-del-Repositorio.md` §2.1): las dos docentes de cálculo pueden
> revisarlo sin leer una línea de programación, y un cambio de contenido no
> exige desplegar el sistema.

## Formato

Un archivo `.md` por fragmento, en [`fragmentos/`](fragmentos/), con cabecera de
metadatos. Los campos obligatorios lo son de verdad: el validador falla si falta alguno.

> **Van en su propia carpeta y no junto a estos documentos.** Con dieciséis conceptos y
> entre diez y treinta fragmentos cada uno, la carpeta raíz del corpus dejaría de servir
> para encontrar nada.

```markdown
---
identificador: F-001
nivel_apos: proceso
registro_duval: algebraico
concepcion_asociada: M21
nodo_grafo: regla-de-la-cadena
procedencia:
  obra: PUR          # clave de FUENTES.md, no el título
  pagina: 119        # página de la EDICIÓN impresa
  captura: mixta     # nativa · mixta · ocr · manual
---

Texto del fragmento.
```

## Por qué esos metadatos y no otros

| Campo | Requisito | Por qué está |
|---|---|---|
| `nivel_apos` | `RF-COR-01` | APOS es el marco predominante del Eje C (8 de 18 estudios) y **el único hallazgo del corpus con certeza CERQual Moderada** |
| `registro_duval` | `RF-COR-01` | Duval distingue tratamiento de conversión. El reordenamiento de `RF-GPE-13` usa el cambio de registro respecto al turno anterior |
| `concepcion_asociada` | `RF-COR-02` | Es la arista que en el experimento E01 produjo **0,800 de recall diagnóstico frente a 0,300** del vectorial: cuando el estudiante enuncia una concepción errónea, la similitud semántica lleva al concepto equivocado y esta arista lo rescata |
| **`procedencia`** | **`DD-15` §Corpus** | El material de las docentes está autorizado **solo para las pruebas del objetivo 4**. Sin procedencia el corpus *«no se puede depurar, solo borrar entero»*. Es además lo que `DD-02` necesita para verificar la matemática al ingerir: sin saber de dónde viene un fragmento, no hay contra qué comprobarlo |

Valores admitidos:

- `nivel_apos`: `accion` · `proceso` · `objeto` · `esquema`
- `registro_duval`: `algebraico` · `grafico` · `numerico` · `verbal`
- `concepcion_asociada`: un identificador del catálogo de 24, o vacío
- `procedencia.obra`: una clave de tres letras de [`FUENTES.md`](FUENTES.md)
- `procedencia.captura`: `nativa` · `mixta` · `ocr` · `manual`

> **`captura` por defecto es `mixta`, y no es casualidad.** Ninguna de las obras conserva
> sus fórmulas al extraerlas —ni siquiera el PDF generado con LaTeX—, así que la prosa se
> extrae y la matemática se transcribe. El campo permite responder después *«¿de dónde
> salió este signo?»* sin volver a abrir el libro. Ver
> [`ESTRATEGIA-DE-EXTRACCION.md`](ESTRATEGIA-DE-EXTRACCION.md).

> ⚠️ **`procedencia` no tiene valor por defecto en `Fragmento`.** Construir uno sin ella
> es un `TypeError`, no un fragmento con un hueco. Que el fallo ocurra al escribir y no el
> día que haya que retirar una obra es el punto entero de `DD-15`.

## Alcance del contenido

Las cuatro concepciones comprometidas son **M21** regla de la cadena, **M22**
derivada del coseno, **M23** constante simbólica frente a variable y **M16**
conjugados en la derivada por definición.

> ⚠️ La **conversión gráfica f↔f′** queda fuera del alcance comprometido pese a
> ser una de las concepciones mejor documentadas, porque depende del componente
> de visualización — el subsistema con menos evidencia, y toda ella procedente
> de contextos presenciales. No se escriben fragmentos para ella.

## Las obras fuente y su procedencia

Desde el 2026-08-05 hay material en `_obras/`: **ocho obras en diez archivos**, aportadas
por las docentes. Dos documentos acompañan a ese material y conviene leerlos antes de
extraer nada:

| Documento | Para qué |
|---|---|
| [`FUENTES.md`](FUENTES.md) | La ficha de cada obra y la clave con la que la cita un fragmento |
| [`ESTRATEGIA-DE-EXTRACCION.md`](ESTRATEGIA-DE-EXTRACCION.md) | Qué hacer con cada una, y por qué la matemática se transcribe en lugar de extraerse |

> ⚠️ **Las obras no se versionan.** `.gitignore` excluye `_obras/`, porque `DD-15`
> autoriza su uso solo para las pruebas del objetivo 4 y **un archivo que entra al
> historial de git ya no se puede retirar**. Quien clone el repositorio no las recibe.

## Estado

| | |
|---|---|
| Esquema y validador | ✅ Incremento 1 |
| Obras fuente inventariadas | ✅ 2026-08-05 — ocho obras, con su diagnóstico de extracción |
| **Procedencia en el esquema del fragmento** | ✅ 2026-08-05 — obligatoria, con 11 pruebas que la cubren |
| Fragmentos escritos | ✅ **271 escritos, 248 indexados** · las cinco obras troceadas están dentro · los 68 últimos son de `PM-C21`, 2026-08-19, y cubren límites, continuidad y el tercer corte |
| Revisión docente | 🟡 Sesión del 2026-08-09 **sin lectura a fondo**; no señalaron correcciones. `PM-X01` sigue abierta |

**El validador ya funciona sin fragmentos**, que es lo que permite que la
autoría avance en paralelo con la construcción sin bloquearla.

---

## Cobertura · que ningún nodo se quede sin material

`verificar-cobertura.py` responde una pregunta que nadie hacía: **¿tiene cada
nodo del grafo al menos un fragmento?** El 2026-08-18 la respuesta fue que no
para tres nodos —`N01` Límite, `N02` Continuidad y `N12` Máximos y mínimos—, que
llevaban meses en cero mientras todos los comprobadores salían en verde.
Preguntar *«¿qué es un límite?»* devolvía procedencia `sin-fuente`.

**No lo veía nadie porque el script que sonaba parecido mide al revés.**

| Script | Pregunta | Qué decía de `N01` |
|---|---|---|
| `grafo/inventario-de-cobertura.py` | ¿Tiene **nodo** este tema del libro? | «Cubierto»: el nodo existía |
| `corpus/verificar-cobertura.py` | ¿Tiene **fragmentos** este nodo? | «Vacío»: cero de 203 |

Un nodo puede existir, tener sinónimos, enrutar consultas y llevarlas a un
estante vacío.

```
python OE3-Implementacion/codigo/contenido/corpus/verificar-cobertura.py
```

Imprime el reparto entero por nodo y devuelve 1 si hay problemas. **Falla** si un
nodo está en cero sin estar declarado en `PENDIENTES` con su motivo, si un
fragmento apunta a un nodo que no existe, o si a un fragmento le falta el
`nodo_grafo` que `DD-22` exige. **Avisa sin fallar** de los nodos con menos de
cuatro fragmentos.

Ninguna cifra está escrita dentro del script: los nodos salen de `grafo.json` y
la cuenta de abrir los archivos, según `COMO-TRABAJAMOS.md` §4.bis. Y se le ha
visto fallar: `pruebas/unidad/test_cobertura_corpus.py` lo rompe a propósito en
cada uno de esos casos.

---

## Los 23 que `DD-02` deja fuera del índice · el encargo de `PM-X01`

**No son trabajo pendiente de código, y por eso están escritos aquí uno por uno.** Se
intentó tres veces resolverlos con más código y cada intento metió un defecto nuevo en el
verificador — el último **aprobaba lo que no sabía leer**, que es el peor de los seis
defectos de la iteración 0 repetido por otra puerta. Lo que falta no es un analizador
mejor: es una lectura humana, y esa lectura es `PM-X01`.

La lista se reproduce con `python verificar-matematica.py` desde esta carpeta, y sale
partida en dos por el motivo, no por el número.

### 19 «abstracto» · enuncian una regla sobre una `f` y una `g` cualesquiera

Un motor simbólico deriva funciones, no cuantificadores. *«Si `f` y `g` son derivables
entonces `(f+g)' = f' + g'`»* no tiene ninguna instancia que evaluar: comprobarlo es
demostrar el teorema, y eso no es lo que `DD-02` pide al ingerir.

| | Qué enuncia |
|---|---|
| `F-005` | Regla de la cadena: si $f = g \circ h$ entonces $f' = g'(h)\,h'$, y el factor $h'$ se llama derivada interna |
| `F-009` | Derivada por definición de $f(x) = x^3 + 7x$ — **la única de las 19 con función concreta**; ver la nota de abajo |
| `F-024` | Múltiplo constante: $(kf)' = k f'$ |
| `F-025` | Suma: $(f+g)' = f' + g'$ |
| `F-030` | Demostración de la regla del producto, con el truco de sumar y restar $f(x+h)g(x)$ |
| `F-033` | Demostración de la regla del cociente |
| `F-126` | Demostración del teorema del valor medio a partir de Rolle, con la función auxiliar $F$ |
| `F-136` | Múltiplo constante, en la notación $D_x$ de `LEI` |
| `F-137` | Suma, en la notación $D_x$ de `LEI` |
| `F-139` | Producto, con el paso de restar y sumar $f(x+\Delta x)g(x)$ |
| `F-140` | Cociente, con el paso de restar y sumar $f(x)g(x)$ |
| `F-142` | Potencia con exponente entero negativo: $f(x) = x^{-n}$ |
| `F-154` | La potencia se extiende a exponente racional: $f(x) = x^{r}$ |
| `F-165` | Derivada de $\log_a x$ **con base $a$ cualquiera**: no hay número que sustituir |
| `F-166` | De dónde sale el factor $\log_a e$, desde el cociente incremental |
| `F-185` | El múltiplo constante como caso del producto tomando $h(x) = c$ |
| `F-187` | Derivada de un polinomio de grado $n$ **genérico**, con puntos suspensivos |
| `F-193` | Tabla de funciones y sus derivadas, sin una ecuación aislada que emparejar |
| `F-199` | Regla de la cadena en `LOP`, y el nombre del factor que se olvida |

> ⚠️ **`F-009` merece que la docente mire el veredicto y no solo el texto.** Su función es
> concreta —$x^3 + 7x$, derivada $3x^2 + 7$— así que «enunciado general» es casi con
> seguridad una lectura equivocada del verificador, no una propiedad del fragmento. **No se
> arregla aquí**: tocar el emparejador es exactamente lo que ya salió mal tres veces.

### 4 «pendiente» · el traductor no supo leer la fórmula, y por eso NO se aprueban

Estos cuatro sí tienen función concreta. Salen fuera porque el analizador se declara
incompetente, que es la conducta correcta: **un verificador que aprueba lo que no entiende
es peor que uno que no verifica.**

| | Qué enuncia | Qué no supo leer |
|---|---|---|
| `F-013` | Derivada de $g(x) = 2/(x+3)$ por la forma $x \to c$ | Afirma $g'(c)$: la derivada va en otra variable que la definición |
| `F-125` | Teorema del valor medio | Afirma $f'(c)$ para un $c$ que el teorema solo garantiza que **existe** |
| `F-152` | Tres derivadas calculadas **sin** la regla de la cadena, y el patrón que aparece | Una de las tres fórmulas no se analiza |
| `F-178` | $y = (\sin x)^{x^2}$, base y exponente distintos | La fórmula lleva $(\sin x)'$ **dentro** de la expresión |

**Ninguno de los 23 es deuda de corpus.** Están escritos, versionados y con procedencia;
lo único que no tienen es una marca que solo puede poner quien lea matemática. Mientras no
la tengan, `cargar()` los deja fuera del índice y lo dice en voz alta, que es lo que
`DD-02` exige.
