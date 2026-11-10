
<script>
  import EnlaceAConcepto from './EnlaceAConcepto.svelte';
  import { esNombreHumano } from '../../nucleo/presentacion/identificadores.js';

  let {
    conceptos = [],
    alAbrir = null
  } = $props();

  const unicos = $derived(
    [...new Map(conceptos.map((c) => [c?.id || c?.nombre, c])).values()]
      .filter((c) => esNombreHumano(c?.nombre))
  );
</script>

{#if unicos.length}
  <aside class="panel" aria-labelledby="panel-conceptos-titulo">
    <h2 id="panel-conceptos-titulo">Para consultar</h2>
    <ul>
      {#each unicos as c (c.id || c.nombre)}
        <li><EnlaceAConcepto concepto={c} {alAbrir} /></li>
      {/each}
    </ul>
  </aside>
{/if}

<style>
  .panel { display: flex; flex-direction: column; }

  h2 {
    margin: 0 0 0.5rem;
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  ul { margin: 0; padding: 0; list-style: none; }

  li {
    display: flex;
    align-items: center;
    min-block-size: 24px;
    padding-block: 0.25rem;
    font-size: var(--texto-sm);
  }
</style>
