<!--
Un bloque con SU PROPIO sello.

Es donde `RP-01` se cumple o se incumple: el sello va por bloque y no por turno,
porque el requisito dice «en cada paso o resultado, no en la respuesta completa».

UN TIPO DESCONOCIDO DEJA UN HUECO VISIBLE. No es un descuido, es la decisión de
`05` §3.2: si el backend estrena un tipo de bloque y aquí no hay componente que
lo pinte, tiene que NOTARSE. Callarlo dejaría al estudiante sin parte de la
respuesta sin que nadie se entere, que es peor que un hueco feo.

`GRAFICA` NO DIBUJA AQUÍ. El servidor emite ese bloque siempre que el cálculo
lo permite —casi todo turno con una derivada válida—, así que el tablero de
verdad (`Grafica.svelte`, interactivo) repetido en cada turno llenaba el hilo
de tableros entre las respuestas. `GraficaCitada.svelte` deja solo la
referencia; el tablero sigue existiendo, en `GaleriaDeTrabajo.svelte`.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import Prosa from './Prosa.svelte';
  import Notacion from './Notacion.svelte';
  import ExpresionCitada from './ExpresionCitada.svelte';
  import GraficaCitada from './GraficaCitada.svelte';
  import SelloVerificacion from '../estado/SelloVerificacion.svelte';

  let {
    /** { tipo, contenido, sello, alternativo } — ver contrato §5 */
    bloque,
    /**
     * ¿Este bloque DEBE llevar sello?
     *
     * `true` para todo lo que afirma el sistema, que es el caso por defecto y
     * el que `RP-01` gobierna. `false` SOLO para lo que escribió el propio
     * estudiante cuando el hilo lo repite: su mensaje no es una afirmación del
     * sistema, así que no hay nada que verificar en él, y pedirle sello hacía
     * que la conversación mostrara «estado de verificación no reconocido»
     * sobre lo que el estudiante acababa de escribir.
     *
     * Quien lo pone en `false` es `Turno.svelte`, que es el único que sabe
     * quién habla. Este componente no lo deduce del contenido: deducirlo sería
     * darle una vía para callar un sello que sí falta.
     */
    sellado = true,
    /**
     * ¿Va dentro de un párrafo, en fila con los bloques de al lado?
     *
     * `ADR-014` parte la narración en cada expresión citada, así que una frase
     * llega como prosa · expresión · prosa. Apiladas se leen como tres cosas
     * distintas, y con un sello cada una son tres sellos idénticos para una
     * sola oración.
     *
     * ⚠️ NO DEBILITA `RP-01`. El sello sigue siendo del bloque en el dato, y
     * quien agrupa —`Turno.svelte`— solo junta bloques **que llevan el mismo
     * sello** y pinta ese sello una vez para la fila. Dos bloques con sellos
     * distintos nunca caen en el mismo párrafo.
     */
    enLinea = false,
    /**
     * El signo que cierra la frase de este bloque, si lo hay.
     *
     * `ADR-014` corta la narración en la referencia, así que «… el resultado es
     * {{a1}}.» deja el punto en un bloque de prosa suelto. Se pinta **pegado a
     * la expresión y antes del sello**, que es donde va en la frase; en su
     * propio párrafo con su propio «Explicación generada» al lado sería ruido.
     * Quien lo separa es `Turno.svelte`, que ve la secuencia.
     */
    cierre = '',
    alAbrirGrafica = null,
    /**
     * ¿Esta cita lleva su propio rótulo «solo mencionado»?
     *
     * Solo aplica a `expresion-citada`. El rótulo es por FRASE, no por bloque
     * —dos citas en una misma oración no repiten la palabra—, y quien decide
     * cuál de las citas es la primera es `Turno.svelte`, que ve el grupo
     * completo. `true` por defecto: una cita sola en su propio párrafo sigue
     * llevando su rótulo.
     */
    rotulado = true
  } = $props();

  const CONOCIDOS = ['prosa', 'notacion', 'expresion-citada', 'grafica'];
  const conocido = $derived(CONOCIDOS.includes(bloque?.tipo));
</script>

<!--
  El interior va en un `snippet` y SIN saltos de línea, porque en fila cada
  salto es un nodo de texto en blanco que separa la expresión del signo que la
  sigue: salía «sen(x^2) : es una composición», con espacio antes del dos
  puntos. En bloque daba igual; dentro de una frase no.
-->
{#snippet interior()}{#if bloque?.tipo === 'prosa'}<Prosa contenido={bloque.contenido} {enLinea} />{:else if bloque?.tipo === 'notacion'}<Notacion expresion={bloque.contenido} alternativo={bloque.alternativo} bloque />{:else if bloque?.tipo === 'expresion-citada'}<ExpresionCitada expresion={bloque.contenido} alternativo={bloque.alternativo} {rotulado} />{:else if bloque?.tipo === 'grafica'}<GraficaCitada definicion={bloque.contenido} alternativo={bloque.alternativo} {alAbrirGrafica} />{:else}<span class="hueco">Esta parte de la respuesta no se pudo mostrar <span class="detalle">(tipo de contenido no reconocido: {bloque?.tipo ?? 'sin tipo'})</span></span>{/if}{/snippet}

{#if enLinea}<span class="bloque en-linea">{@render interior()}</span>{:else}
  <div class="bloque">
    <span class="contenido">{@render interior()}{#if cierre}<span class="cierre">{cierre}</span>{/if}</span>
    <!-- En fila, el sello lo pinta el párrafo una sola vez: ver `enLinea`. -->
    {#if conocido && sellado}
      <SelloVerificacion estado={bloque.sello} />
    {/if}
  </div>
{/if}

<style>
  .bloque {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
    margin-block-end: 0.9rem;
  }

  /* Dentro de un párrafo no manda la caja: manda el texto que la rodea. */
  .bloque.en-linea {
    display: inline;
    margin-block-end: 0;
  }

  /* La expresión y el signo que cierra su frase comparten línea base. En un
     bloque independiente la caja también ocupa el ancho disponible: dejarla
     como `inline-flex` encogía la prosa del asistente y creaba una columna
     vacía dentro de una burbuja deliberadamente ancha. Los bloques que sí van
     dentro de una frase usan `.bloque.en-linea` y no pasan por esta caja. */
  .contenido {
    display: flex;
    align-items: baseline;
    inline-size: 100%;
    min-inline-size: 0;
  }

  /* El hueco se ve. Es intencionado. */
  .hueco {
    display: block;
    margin: 0;
    padding: 0.6rem 0.8rem;
    inline-size: 100%;
    background: var(--semantic-warning-bg);
    border: 1px dashed var(--semantic-warning);
    border-radius: var(--radius-sm);
    color: var(--semantic-warning);
    font-size: var(--texto-sm);
  }

  .detalle { display: block; font-size: var(--texto-xs); }
</style>
