
<script>
  let {
    tipo = 'button',
    variante = 'principal',
    deshabilitado = false,
    href = null,
    children,
    ...resto
  } = $props();
</script>

{#if href}
<a {href} class="boton {variante}" {...resto}>
  {@render children?.()}
</a>
{:else}
<button type={tipo} class="boton {variante}" disabled={deshabilitado} {...resto}>
  {@render children?.()}
</button>
{/if}

<style>
  .boton {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5em;
    padding: 0.55em 1.1em;
    border: 1px solid transparent;
    border-radius: var(--radius-trazado);
    font-size: var(--texto-base);
    font-weight: 500;
    line-height: 1.2;
    text-decoration: none;
    transition: var(--transition-fast);
  }

  .principal  { background: var(--accent-main); color: var(--surface-paper); }

  .secundario { background: var(--surface-paper); color: var(--ink-primary);
                border-color: var(--trazo); }
  .discreto   { background: transparent; color: var(--ink-secondary); }
  .exito { background: var(--semantic-success-bg); color: var(--semantic-success); border-color: var(--semantic-success); }

  .boton {
    transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .principal:hover:not(:disabled)  {
    background: var(--accent-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--accent-glow);
  }
  .secundario:hover:not(:disabled) {
    background: var(--surface-panel);
    transform: translateY(-1px);
    box-shadow: var(--shadow-soft);
  }
  .discreto:hover:not(:disabled)   { color: var(--ink-primary);
                                     border-color: var(--trazo);
                                     background: var(--accent-surface); }

  .boton:active:not(:disabled) { transform: translateY(0) scale(0.97); }

  .boton:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
