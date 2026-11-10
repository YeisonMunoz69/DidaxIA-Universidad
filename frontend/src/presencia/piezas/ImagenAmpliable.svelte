<script>
  let { src, alt, descripcion = '', clase = '', width, height } = $props();

  let visor = $state(null);
  const idTitulo = $derived(
    `titulo-${(src.split('/').at(-1) ?? 'imagen').replace(/\.[^.]+$/, '').replace(/[^a-z0-9-]/gi, '-')}`
  );

  function ampliar() {
    visor?.showModal();
  }

</script>

<figure class={['imagen-ampliable', clase].filter(Boolean).join(' ')}>
  <button
    class="abrir-imagen"
    type="button"
    aria-haspopup="dialog"
  aria-label={`Ampliar imagen: ${alt}`}
    onclick={ampliar}
  >
    <img {src} {alt} {width} {height} loading="lazy" decoding="async" />
    <span class="ayuda-ampliar" aria-hidden="true">Ampliar vista <span>↗</span></span>
  </button>
  {#if descripcion}
    <figcaption>{descripcion}</figcaption>
  {/if}
</figure>

<dialog
  bind:this={visor}
  class="visor-imagen"
  aria-labelledby={idTitulo}
>
  <div class="contenido-visor">
    <div class="cabecera-visor">
      <h2 id={idTitulo}>{descripcion || 'Vista ampliada'}</h2>
      <button class="cerrar-visor" type="button" onclick={() => visor?.close()}>
        Cerrar <span aria-hidden="true">×</span>
      </button>
    </div>
    <img class="imagen-visor" {src} {alt} />
    <p class="sr-only">{alt}</p>
  </div>
</dialog>

<style>
  .imagen-ampliable {
    min-inline-size: 0;
    margin: 0;
  }

  .abrir-imagen {
    position: relative;
    display: block;
    inline-size: 100%;
    padding: 0;
    overflow: hidden;
    border: 0;
    border-radius: var(--radius-lg);
    color: var(--ink-primary);
    background: var(--surface-canvas);
    cursor: zoom-in;
    text-align: start;
  }

  .abrir-imagen img {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    object-fit: cover;
    transition: transform 200ms ease;
  }

  .abrir-imagen:hover img { transform: scale(1.018); }

  .abrir-imagen:focus-visible,
  .cerrar-visor:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 3px;
  }

  .ayuda-ampliar {
    position: absolute;
    inset-inline-end: var(--espacio-sm);
    inset-block-end: var(--espacio-sm);
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-xs);
    padding: 0.35rem 0.55rem;
    border-radius: var(--radius-trazado);
    color: var(--ink-primary);
    background: var(--surface-paper);
    font-size: var(--texto-xs);
    font-weight: 600;
    opacity: 0;
    transform: translateY(3px);
    transition: opacity 180ms ease, transform 180ms ease;
  }

  .abrir-imagen:hover .ayuda-ampliar,
  .abrir-imagen:focus-visible .ayuda-ampliar { opacity: 1; transform: none; }

  figcaption {
    margin-block-start: var(--espacio-xs);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    line-height: var(--interlinea-normal);
  }

  .visor-imagen {
    inline-size: min(96vw, 88rem);
    max-inline-size: 96vw;
    max-block-size: 94dvh;
    padding: var(--espacio-lg);
    overflow: auto;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-xl);
    color: var(--ink-primary);
    background: var(--surface-paper);
    box-shadow: var(--shadow-float);
  }

  .visor-imagen::backdrop { background: var(--velo-modal); }

  .contenido-visor {
    display: grid;
    gap: var(--espacio-md);
  }

  .cabecera-visor {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: var(--espacio-md);
  }

  .cabecera-visor h2 {
    margin: 0;
    font-size: var(--texto-base);
    line-height: var(--interlinea-normal);
  }

  .cerrar-visor {
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-xs);
    min-block-size: 44px;
    padding: 0.4rem 0.7rem;
    border: 0;
    border-radius: var(--radius-trazado);
    color: var(--ink-secondary);
    background: transparent;
    cursor: pointer;
  }

  .cerrar-visor:hover { color: var(--ink-primary); background: var(--surface-canvas); }

  .imagen-visor {
    display: block;
    inline-size: 100%;
    max-block-size: calc(94dvh - 8rem);
    object-fit: contain;
    border-radius: var(--radius-md);
    background: var(--surface-canvas);
  }

  .sr-only {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }

  @media (prefers-reduced-motion: reduce) {
    .abrir-imagen img,
    .ayuda-ampliar { transition: none; }
    .abrir-imagen:hover img { transform: none; }
  }
</style>
