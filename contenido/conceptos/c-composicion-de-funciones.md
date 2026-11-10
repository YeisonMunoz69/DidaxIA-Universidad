# C-composicion-de-funciones · Qué hay dentro de qué

> ⚠️ **Contenido, no código.** Este archivo lo revisan y corrigen las docentes.
> No se genera por script. Ver `OE3-Implementacion/04-Decisiones-de-Detalle.md` `DD-13`.

| | |
|---|---|
| **Identificador** | `C-composicion-de-funciones` |
| **Nodo del grafo** | `N08` |
| **Concepción errónea asociada** | — · **no es una concepción errónea, es un prerrequisito** |
| **Estado** | 🟡 Borrador · **pendiente de revisión docente** |

---

## Qué es

Componer dos funciones es **aplicar una al resultado de la otra**: $(g \circ h)(x)$
significa calcular primero $h(x)$ y meter ese número en $g$. El orden no es
intercambiable, y ahí está todo.

Es prerrequisito de la regla de la cadena, y de los duros: **la regla no falla por la
fórmula, falla porque la composición no se ve**.

## Cómo se manifiesta

Lo que ocurre cuando este prerrequisito no está:

- No distinguir $\sin(x^2)$ de $(\sin x)^2$: mismas letras, composiciones opuestas
- Leer $\cos^3 x$ como una función simple, cuando son tres encajadas
- Creer que $g \circ h$ y $h \circ g$ son la misma cosa
- No saber decir cuál es «la de dentro» ante una expresión con paréntesis

## Qué hay que entender antes

Estas son las **aristas de prerrequisito**. El grafo las usa para decidir si el fallo está
aquí o en algo anterior.

| Concepto previo | Por qué |
|---|---|
| `C-variable-de-derivacion` | Para componer hay que saber qué papel juega cada letra: cuál es el argumento y cuál es el resultado |

## La explicación

La prueba práctica no es algebraica: **¿en qué orden apretaría las teclas de la
calculadora?** Para $\sin(x^2)$ se teclea el número, se eleva al cuadrado y **después** se
pulsa seno. Para $(\sin x)^2$ es al revés. Ese orden **es** la composición.

Y una vez visto, la regla de la cadena se lee sola: **recorre ese orden al revés**. La
última tecla que se pulsó es la primera función que se deriva, evaluada en lo que había
antes; luego se multiplica por la derivada de lo de dentro.

Conviene además nombrar las capas en voz alta —*«raíz de, un polinomio de, x»*— porque
poner nombre a cada capa es lo que impide saltársela al derivar.

## Qué muestra la simulación

> Esto es lo que `Simulacion.svelte` interpreta. **Describe qué ocurre al mover los
> parámetros, no solo qué se dibuja.**

- Una expresión compuesta con **cada capa resaltable por separado**; al señalar una, se
  muestra qué se evalúa antes y qué después.
- Un número de entrada que **viaja por las capas** una a una, mostrando el valor
  intermedio en cada paso.
- $\sin(x^2)$ y $(\sin x)^2$ lado a lado, con el mismo número de entrada recorriendo las
  dos y **llegando a resultados distintos**.
- Un modo «invertir el orden» que compone al revés y muestra que sale otra función.

---

## Procedencia

**No sale del catálogo de 24 concepciones**: es un concepto de apoyo, de los que
`MAPA-M01-M24.md` llama la tanda 2. Existe porque `C-M21` lo declaraba como su
prerrequisito real y el banco no lo tenía — era una arista rota que
`verificar-conceptos.py` listaba en cada corrida.

El corpus lo cubre desde `PM-C07`: `LEI` §1.2 trae la composición de funciones, y los
fragmentos que la desarrollan cuelgan de `N08`.

## Qué falta en este archivo

- [ ] Revisión de una docente de cálculo
- [ ] Descripción textual alternativa de la simulación, obligatoria por `DD-05`
- [ ] Comprobación matemática al ingerir, según `DD-02`

---

*Banco de conceptos · `DD-13` · IU Colegio Mayor del Cauca*
