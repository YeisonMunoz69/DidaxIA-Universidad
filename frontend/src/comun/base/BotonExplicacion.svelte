<script>
  import BotonAyudaTooltip from './BotonAyudaTooltip.svelte';
  let { etiqueta, alAbrir, abierto = false, texto = 'Abre la explicación completa: cálculo, ejemplo, fuentes e interpretación.' } = $props();
</script>
<span class="acciones-explicacion">
  <button type="button" class="expandir" aria-label={etiqueta} aria-expanded={abierto} onclick={alAbrir}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M9 4H4v5M15 4h5v5M4 15v5h5M20 15v5h-5M4 4l6 6M20 4l-6 6M4 20l6-6M20 20l-6-6" />
    </svg>
  </button>
  <BotonAyudaTooltip tamano="sm" {texto} ariaLabel={`Qué hace el botón: ${etiqueta}`} />
</span>
<style>
  .acciones-explicacion { display: inline-flex; align-items: center; flex: none; gap: .15rem; }
  .expandir { display: grid; place-items: center; inline-size: 44px; block-size: 44px; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); cursor: pointer; }
  svg { inline-size: 21px; block-size: 21px; }
  .expandir:hover { background: var(--surface-panel); border-color: var(--help-color); color: var(--help-color); }
  .expandir:focus-visible { outline: 2px solid var(--help-color); outline-offset: 2px; }
</style>
