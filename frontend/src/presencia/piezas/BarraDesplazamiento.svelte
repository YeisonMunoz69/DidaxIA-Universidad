
<script>
  import { onDestroy } from 'svelte';

  let {
    contenedor = null
  } = $props();

  let elementoPista = $state(null);
  let alturaThumb = $state(48);
  let posicionThumb = $state(0);
  let arrastrando = $state(false);
  let visible = $state(true);
  let temporizadorOcultar = null;

  let inicioY = 0;
  let scrollInicial = 0;

  function recalcular() {
    if (!contenedor || !elementoPista) return;

    const scrollTotal = contenedor.scrollHeight;
    const alturaVisible = contenedor.clientHeight;
    const alturaPista = elementoPista.clientHeight;

    if (scrollTotal <= alturaVisible || alturaPista <= 0) {
      alturaThumb = 0;
      return;
    }

    const proporcion = alturaVisible / scrollTotal;
    const minAltura = 40;
    const alturaCalculada = Math.max(minAltura, Math.round(alturaPista * proporcion));
    alturaThumb = alturaCalculada;

    const espacioRecorrido = scrollTotal - alturaVisible;
    const espacioPista = alturaPista - alturaCalculada;
    const progreso = espacioRecorrido > 0 ? contenedor.scrollTop / espacioRecorrido : 0;

    posicionThumb = Math.max(0, Math.min(espacioPista, Math.round(progreso * espacioPista)));
  }

  function mostrarYDesvanecer() {
    visible = true;
    if (temporizadorOcultar) clearTimeout(temporizadorOcultar);
    if (!arrastrando) {
      temporizadorOcultar = setTimeout(() => {
        visible = false;
      }, 1600);
    }
  }

  function alScrollContenedor() {
    recalcular();
    mostrarYDesvanecer();
  }

  function alPulsarThumb(e) {
    e.preventDefault();
    e.stopPropagation();
    arrastrando = true;
    visible = true;
    inicioY = e.clientY;
    scrollInicial = contenedor.scrollTop;

    window.addEventListener('pointermove', alMoverPuntero);
    window.addEventListener('pointerup', alSoltarPuntero);
  }

  function alMoverPuntero(e) {
    if (!arrastrando || !contenedor || !elementoPista) return;

    const deltaY = e.clientY - inicioY;
    const alturaPista = elementoPista.clientHeight;
    const espacioPista = alturaPista - alturaThumb;
    const espacioScroll = contenedor.scrollHeight - contenedor.clientHeight;

    if (espacioPista <= 0) return;

    const ratio = espacioScroll / espacioPista;
    contenedor.scrollTop = scrollInicial + deltaY * ratio;
  }

  function alSoltarPuntero() {
    arrastrando = false;
    mostrarYDesvanecer();
    window.removeEventListener('pointermove', alMoverPuntero);
    window.removeEventListener('pointerup', alSoltarPuntero);
  }

  function alClicEnPista(e) {
    if (e.target.closest('.pulgar-scroll')) return;
    if (!contenedor || !elementoPista) return;

    const rect = elementoPista.getBoundingClientRect();
    const clicY = e.clientY - rect.top;
    const alturaPista = elementoPista.clientHeight;
    const espacioPista = alturaPista - alturaThumb;
    const espacioScroll = contenedor.scrollHeight - contenedor.clientHeight;

    const objetivoThumb = clicY - alturaThumb / 2;
    const progreso = Math.max(0, Math.min(1, objetivoThumb / espacioPista));

    contenedor.scrollTo({
      top: progreso * espacioScroll,
      behavior: 'smooth'
    });
  }

  $effect(() => {
    if (contenedor) {
      recalcular();
      contenedor.addEventListener('scroll', alScrollContenedor, { passive: true });
      window.addEventListener('resize', recalcular, { passive: true });

      return () => {
        contenedor.removeEventListener('scroll', alScrollContenedor);
        window.removeEventListener('resize', recalcular);
      };
    }
  });

  onDestroy(() => {
    if (temporizadorOcultar) clearTimeout(temporizadorOcultar);
    if (typeof window !== 'undefined') {
      window.removeEventListener('pointermove', alMoverPuntero);
      window.removeEventListener('pointerup', alSoltarPuntero);
    }
  });
</script>


{#if alturaThumb > 0}
  <button
    type="button"
    class="pista-scroll"
    class:visible={visible || arrastrando}
    bind:this={elementoPista}
    onclick={alClicEnPista}
    tabindex="-1"
    aria-label="Desplazar página"
  >
    <span
      class="pulgar-scroll"
      class:arrastrando
      style:height="{alturaThumb}px"
      style:transform="translate(-50%, {posicionThumb}px)"
      onpointerdown={alPulsarThumb}
      role="presentation"
    >
      <span class="nucleo-pulgar"></span>
    </span>
  </button>
{/if}

<style>
  .pista-scroll {
    position: fixed;
    display: block;
    inset-inline-end: 8px;
    inset-block-start: 70px;
    inset-block-end: 16px;
    inline-size: 14px;
    background: var(--surface-glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--trazo-suave);
    padding: 0;
    margin: 0;
    z-index: 150;
    pointer-events: auto;
    opacity: 0.45;
    transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1), inline-size var(--transition-fast);
    border-radius: var(--radius-xl);
  }

  .pista-scroll.visible,
  .pista-scroll:hover {
    opacity: 1;
  }

  .pulgar-scroll {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translate(-50%, 0);
    inline-size: 10px;
    border-radius: var(--radius-xl);
    cursor: grab;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: inline-size var(--transition-fast), transform 0.05s linear;
  }

  .pulgar-scroll.arrastrando {
    cursor: grabbing;
    inline-size: 12px;
  }

  .nucleo-pulgar {
    inline-size: 100%;
    block-size: 100%;
    border-radius: var(--radius-xl);
    background-color: var(--ink-secondary);
    box-shadow: var(--shadow-soft);
    border: 1px solid var(--trazo-suave);
    transition: background-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .pista-scroll:hover .nucleo-pulgar {
    background-color: var(--accent-main);
    box-shadow: var(--shadow-float);
  }

  .pulgar-scroll.arrastrando .nucleo-pulgar {
    background-color: var(--accent-hover);
    box-shadow: var(--shadow-float);
  }

  @media (max-width: 48rem) {
    .pista-scroll {
      display: none !important;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .pista-scroll {
      transition: none;
    }
    .pulgar-scroll {
      transition: none;
    }
  }
</style>
