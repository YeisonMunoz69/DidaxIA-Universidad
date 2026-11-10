
<script>
  import { ayudaContextual } from '../base/ayudaContextual.js';
  import Icono from '../base/Icono.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { historial } from '../../nucleo/historial/historial.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { inicioDe } from '../../enrutado/caminos.js';
  import { espacio } from '../../nucleo/espacio/espacio.svelte.js';

  let { carrilAbierto = $bindable(false), compacto = false } = $props();
  let empezando = $state(false);

  async function empezarConversacion() {
    if (empezando) return;
    empezando = true;
    carrilAbierto = false;
    try {
      await sesion.reiniciarConversacion();
      historial.volver();
      navegar(inicioDe(sesion.rol, espacio.activo));
    } finally {
      empezando = false;
    }
  }
</script>

<button use:ayudaContextual class="nueva" class:compacta={compacto} onclick={empezarConversacion} disabled={empezando}
        aria-label={compacto ? 'Nueva conversación' : undefined} title={compacto ? 'Nueva conversación' : undefined}>
  <Icono nombre="nueva" medida={16} />
  {#if !compacto}{empezando ? 'Empezando…' : 'Nueva conversación'}{/if}
</button>

<style>
  .nueva {
    flex-shrink: 0;
    inline-size: 100%;
    min-block-size: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5em;
    margin-block-end: 24px;
    padding: 12px 18px;
    background: var(--ink-primary);
    color: var(--surface-paper);
    border: none;
    border-radius: var(--radius-sm);
    font-size: var(--texto-sm);
    font-weight: 600;
    letter-spacing: 0.01em;
    cursor: pointer;
    transition: var(--transition);
  }

  .nueva :global(svg) {
    transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .nueva:hover:not(:disabled) {
    background: var(--accent-main);
    color: var(--surface-paper);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px var(--accent-glow);
  }

  .nueva:hover:not(:disabled) :global(svg) {
    transform: rotate(90deg) scale(1.15);
  }

  .nueva:active:not(:disabled) { transform: translateY(0) scale(0.98); }

  .nueva.compacta {
    inline-size: 42px;
    block-size: 42px;
    min-block-size: 42px;
    margin: 0;
    padding: 0;
    border: 1px solid var(--trazo-suave);
    background: transparent;
    color: var(--ink-secondary);
  }
</style>
