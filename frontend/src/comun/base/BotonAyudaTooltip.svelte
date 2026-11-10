<script>
  import { ayudaContextual } from './ayudaContextual.js';
  import Icono from './Icono.svelte';
  let { texto, posicion = 'arriba', tamano = 'md', ariaLabel = '', icono = '' } = $props();
</script>
<button type="button" class="tooltip-container" class:conversacion={icono === 'conversacion'} class:sm={tamano === 'sm'} class:lg={tamano === 'lg'}
  use:ayudaContextual={{ texto, movil: true, posicion }}
  aria-label={ariaLabel || `Ayuda: ${texto}`} aria-expanded="false">
  {#if icono}<Icono nombre={icono} medida={tamano === 'sm' ? 18 : 24} />{:else}<svg viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
    <circle cx="12" cy="12" r="9.5" stroke="currentColor" />
    <path d="M9.7 9a2.5 2.5 0 1 1 3.6 2.2c-.9.5-1.3 1-1.3 2.1" stroke="currentColor" stroke-linecap="round" />
    <circle cx="12" cy="16.6" r=".8" fill="currentColor" />
  </svg>{/if}
</button>
<style>
  .tooltip-container { display: inline-grid; place-items: center; flex: none; inline-size: 36px; block-size: 36px; padding: 0; border: 0; border-radius: 50%; background: transparent; color: var(--help-color); cursor: help; vertical-align: middle; }
  .tooltip-container.sm { inline-size: 32px; block-size: 32px; }
  .tooltip-container.lg { inline-size: 44px; block-size: 44px; }
  .tooltip-container :global(svg) { inline-size: 24px; block-size: 24px; transition: transform .4s cubic-bezier(.34,1.56,.64,1); }
  .sm :global(svg) { inline-size: 18px; block-size: 18px; }
  .tooltip-container:focus-visible { outline: 2px solid var(--help-color); outline-offset: 3px; }
  .tooltip-container:focus-visible :global(svg) { transform: rotate(360deg) scale(1.15); }
  .tooltip-container.conversacion:focus-visible :global(svg) { transform: scale(1.1); }
  @media (hover: hover) { .tooltip-container:hover :global(svg) { transform: rotate(360deg) scale(1.15); } .tooltip-container.conversacion:hover :global(svg) { transform: scale(1.1); } }
  @media (pointer: coarse) { .tooltip-container, .tooltip-container.sm { inline-size: 44px; block-size: 44px; } }
  @media (prefers-reduced-motion: reduce) { .tooltip-container :global(svg) { transition: none; } }
</style>
