<!--
Referencia a una gráfica, no la gráfica misma.

El servidor emite el bloque `grafica` siempre que el cálculo simbólico lo
permite —`08-Contrato-del-Turno.md` §12, `_bloque_grafica()` en
`turno.py`—, así que casi todo turno con una derivada válida traía uno. Con
el tablero de verdad —`Grafica.svelte`, interactivo, 135px— repetido
turno tras turno, la conversación se llenaba de tableros entre las
respuestas y no era ella la que se seguía leyendo.

El tablero de verdad sigue existiendo: vive en `GaleriaDeTrabajo.svelte`,
el panel de «Material de Apoyo», que ya recorre el mismo hilo. Esto es la
mitad que queda en el hilo — dice que hay una gráfica y de qué es, sin
volver a dibujarla — y `alternativo` es lo único que hace falta para
decirlo, porque ya es la descripción completa que el servidor exige por
`RU-10`.



-->
<script>
  import Icono from '../base/Icono.svelte';
  import Notacion from './Notacion.svelte';

  let { definicion = null, alternativo = '', alAbrirGrafica = null } = $props();
  let visitada = $state(false);

  const expresion = $derived.by(() => {
    if (!definicion) return '';
    try {
      let valor = JSON.parse(definicion)?.expresion?.trim?.() ?? '';
      if (valor.startsWith('$$') && valor.endsWith('$$')) valor = valor.slice(2, -2).trim();
      else if (valor.startsWith('$') && valor.endsWith('$')) valor = valor.slice(1, -1).trim();
      else if (valor.startsWith('\\(') && valor.endsWith('\\)')) valor = valor.slice(2, -2).trim();
      return valor ? `f(x) = ${valor}` : '';
    } catch {
      return '';
    }
  });
</script>

<button class="cita-grafica" class:visitada type="button" disabled={!alAbrirGrafica}
        aria-label={`Abrir ${alternativo || 'gráfica matemática'}`}
        onclick={(evento) => { visitada = true; alAbrirGrafica?.(definicion, evento.currentTarget); }}>
  <Icono nombre="grafica" medida={14} />
  <span class="texto">Abrir gráfica de</span>
  {#if expresion}
    <Notacion expresion={expresion} {alternativo} compacto agrandar />
  {:else}
    <span class="texto">{alternativo || 'función disponible en «Material de Apoyo»'}</span>
  {/if}
</button>

<style>
  .cita-grafica {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    padding: 0.3em 0.7em;
    background: var(--surface-panel);
    border: 1px dashed var(--trazo);
    border-radius: var(--radius-pill, 9999px);
    color: var(--ink-secondary);
    font: inherit;
    cursor: pointer;
    text-align: start;
    max-inline-size: 100%;
    overflow-x: auto;
    animation: pulso-grafica 2.3s ease-out 3;
  }

  .cita-grafica.visitada, .cita-grafica:disabled { animation: none; }
  .cita-grafica:disabled { cursor: default; }
  .cita-grafica:not(:disabled):hover { border-color: var(--accent-main); background: var(--accent-surface); }
  .cita-grafica:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }

  @keyframes pulso-grafica {
    0%, 100% { box-shadow: 0 0 0 0 transparent; }
    50% { box-shadow: 0 0 0 5px var(--accent-glow); }
  }
  @media (prefers-reduced-motion: reduce) {
    .cita-grafica { animation: none; }
  }

  .texto {
    font-size: var(--texto-sm);
    line-height: 1.3;
  }

  .cita-grafica :global(.notacion) { white-space: nowrap; }
</style>
