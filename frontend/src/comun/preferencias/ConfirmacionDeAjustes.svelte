<script>
  import Icono from '../base/Icono.svelte';

  let { mensaje } = $props();
</script>

<div class="overlay-confirmacion" aria-live="polite">
  <div class="tarjeta-exito">
    <div class="circulo-check-exito">
      <Icono nombre="check" medida={28} />
    </div>
    <h3 class="titulo-exito">{mensaje.titulo}</h3>
    <p class="sub-exito">{mensaje.sub}</p>
  </div>
</div>

<style>
  .overlay-confirmacion {
    position: absolute;
    inset: 0;
    background: var(--surface-elevated);
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 20;
    animation: aparecerOverlay 0.2s cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes aparecerOverlay {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
  }

  .tarjeta-exito {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--espacio-xs);
    padding: var(--espacio-lg);
    background: var(--surface-paper);
    border: 1.5px solid var(--semantic-success);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card-hover);
    max-inline-size: 20rem;
    animation: popIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes popIn {
    from { transform: scale(0.88); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .circulo-check-exito {
    inline-size: 52px;
    block-size: 52px;
    border-radius: 50%;
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
    border: 1.5px solid var(--semantic-success);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-block-end: var(--espacio-xs);
  }

  .circulo-check-exito :global(svg) { stroke-width: 2.5px; }

  .titulo-exito {
    font-size: var(--texto-base);
    font-weight: 700;
    color: var(--ink-primary);
    margin: 0;
  }

  .sub-exito {
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    margin: 0;
  }
</style>
