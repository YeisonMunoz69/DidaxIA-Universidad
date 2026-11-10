
<script>
  import Icono from '../../comun/base/Icono.svelte';

  let { filtro = $bindable('') } = $props();
</script>

<div class="caja-buscador">
  <Icono nombre="buscar" medida={14} />
  <input
    type="search"
    placeholder="Buscar por tema o palabra clave…"
    bind:value={filtro}
    aria-label="Buscar conceptos" />
  {#if filtro}
    <button
      type="button"
      class="btn-limpiar-busqueda"
      aria-label="Limpiar búsqueda"
      onclick={() => (filtro = '')}>
      <Icono nombre="cerrar" medida={12} />
    </button>
  {/if}
</div>

<style>
  .caja-buscador {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    transition: var(--transition);
    flex-shrink: 0;
  }

  .caja-buscador:focus-within {
    border-color: var(--accent-main);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }

  input {
    flex: 1;
    border: none;
    background: transparent;
    font-family: inherit;
    font-size: 0.75rem;
    color: var(--ink-primary);
    outline: none;
    padding: 0;
  }

  input::-webkit-search-decoration,
  input::-webkit-search-cancel-button,
  input::-webkit-search-results-button,
  input::-webkit-search-results-decoration {
    display: none;
    -webkit-appearance: none;
  }

  .btn-limpiar-busqueda {
    background: transparent;
    border: none;
    padding: 2px;
    color: var(--ink-tertiary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-xs);
    transition: var(--transition-fast);
  }

  .btn-limpiar-busqueda:hover {
    color: var(--ink-primary);
    background: var(--surface-panel);
  }
</style>
