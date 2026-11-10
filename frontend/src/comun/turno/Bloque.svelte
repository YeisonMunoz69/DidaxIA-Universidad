
<script>
  import Prosa from './Prosa.svelte';
  import Notacion from './Notacion.svelte';
  import ExpresionCitada from './ExpresionCitada.svelte';
  import GraficaCitada from './GraficaCitada.svelte';
  import SelloVerificacion from '../estado/SelloVerificacion.svelte';

  let {
    bloque,
    sellado = true,
    enLinea = false,
    cierre = '',
    alAbrirGrafica = null,
    rotulado = true
  } = $props();

  const CONOCIDOS = ['prosa', 'notacion', 'expresion-citada', 'grafica'];
  const conocido = $derived(CONOCIDOS.includes(bloque?.tipo));
</script>


{#snippet interior()}{#if bloque?.tipo === 'prosa'}<Prosa contenido={bloque.contenido} {enLinea} />{:else if bloque?.tipo === 'notacion'}<Notacion expresion={bloque.contenido} alternativo={bloque.alternativo} bloque />{:else if bloque?.tipo === 'expresion-citada'}<ExpresionCitada expresion={bloque.contenido} alternativo={bloque.alternativo} {rotulado} />{:else if bloque?.tipo === 'grafica'}<GraficaCitada definicion={bloque.contenido} alternativo={bloque.alternativo} {alAbrirGrafica} />{:else}<span class="hueco">Esta parte de la respuesta no se pudo mostrar <span class="detalle">(tipo de contenido no reconocido: {bloque?.tipo ?? 'sin tipo'})</span></span>{/if}{/snippet}

{#if enLinea}<span class="bloque en-linea">{@render interior()}</span>{:else}
  <div class="bloque">
    <span class="contenido">{@render interior()}{#if cierre}<span class="cierre">{cierre}</span>{/if}</span>

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

  .bloque.en-linea {
    display: inline;
    margin-block-end: 0;
  }

  .contenido {
    display: flex;
    align-items: baseline;
    inline-size: 100%;
    min-inline-size: 0;
  }

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
