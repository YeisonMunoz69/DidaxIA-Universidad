# C-composicion-de-funciones · Qué hay dentro de qué

| | |
|---|---|
| **Identificador** | `C-composicion-de-funciones` |
| **Nodo del grafo** | `N08` |
| **Concepción errónea asociada** | `— · **no es una concepción errónea, es un prerrequisito**` |
| **Estado** | Borrador · pendiente de revisión docente |

## Qué es

Componer dos funciones es **aplicar una al resultado de la otra**: $(g \circ h)(x)$
significa calcular primero $h(x)$ y meter ese número en $g$. El orden no es
intercambiable, y ahí está todo.

Es prerrequisito de la regla de la cadena, y de los duros: **la regla no falla por la
fórmula, falla porque la composición no se ve**.

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

- Una expresión compuesta con **cada capa resaltable por separado**; al señalar una, se
  muestra qué se evalúa antes y qué después.
- Un número de entrada que **viaja por las capas** una a una, mostrando el valor
  intermedio en cada paso.
- $\sin(x^2)$ y $(\sin x)^2$ lado a lado, con el mismo número de entrada recorriendo las
  dos y **llegando a resultados distintos**.
- Un modo «invertir el orden» que compone al revés y muestra que sale otra función.

## Qué hay que entender antes

| Concepto previo | Por qué |
|---|---|
| `C-variable-de-derivacion` | Para componer hay que saber qué papel juega cada letra: cuál es el argumento y cuál es el resultado |
