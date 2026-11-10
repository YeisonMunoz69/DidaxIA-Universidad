
<script>
  let {
    anchoMaximo = 'min(78rem, 100%)',
    relleno = 'var(--espacio-xl) var(--espacio-lg)',
    espacio = 'var(--espacio-lg)',
    children
  } = $props();
</script>

<div class="desplazable">
  <section
    class="contenido"
    style:max-inline-size={anchoMaximo}
    style:padding={relleno}
    style:gap={espacio}
  >
    {@render children()}
  </section>
</div>

<style>
  .desplazable {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    inline-size: 100%;
  }

  .contenido {
    display: flex;
    flex-direction: column;
    margin-inline: auto;
    animation: entrarVista 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .contenido:has(> :global(.cargador-cubo.pantalla-completa)) {
    min-block-size: 100%;
    box-sizing: border-box;
  }

  @keyframes entrarVista {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (prefers-reduced-motion: reduce) {
    .contenido { animation: none; }
  }
</style>
