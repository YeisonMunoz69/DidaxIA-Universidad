
<script>
  let {
    concepto,
    alAbrir = null
  } = $props();

  const conocido = $derived(Boolean(concepto?.id));
</script>

{#if conocido && typeof alAbrir === 'function'}
  <button type="button" class="enlace" onclick={() => alAbrir(concepto.id)}>
    {concepto.nombre}
  </button>
{:else}
  <span class="suelto">
    {concepto?.nombre ?? 'concepto sin nombre'}
    {#if !conocido}
      <span class="nota">(todavía no está en el banco)</span>
    {/if}
  </span>
{/if}

<style>
  .enlace {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 8px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    color: var(--ink-primary);
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    text-align: start;
    text-decoration: none;
    cursor: pointer;
    box-shadow: var(--shadow-soft);
    transition: var(--transition);
  }

  .enlace:hover {
    background: var(--accent-surface);
    color: var(--accent-main);
    border-color: var(--accent-main);
    transform: translateY(-1px);
    box-shadow: 0 3px 8px var(--accent-glow);
  }

  .suelto {
    display: flex;
    flex-direction: column;
    padding: 8px 12px;
    background: var(--surface-paper);
    border: 1px dashed var(--ink-ghost);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font-size: 13px;
  }

  .nota { font-size: 11px; color: var(--ink-tertiary); margin-top: 2px; }
</style>
