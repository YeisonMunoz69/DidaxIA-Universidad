<script>
  import { onMount } from 'svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { crearOceano, AZUL_DEEPSEEK } from './ballenaDeepSeek.js';
  import { TRAZO_DEEPSEEK } from './trazoDeepSeek.js';

  let { modo = 'normal', amplio = false } = $props();
  let canvas, agua;
  let motor = $state.raw(null);
  let pausada = $state(false);
  let movimientoReducido = $state(false);
  const quieta = $derived(movimientoReducido || !preferencias.animaciones);

  onMount(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const cambiarMovimiento = () => { movimientoReducido = media?.matches ?? true; };
    cambiarMovimiento();
    media?.addEventListener('change', cambiarMovimiento);
    motor = crearOceano(canvas, agua);
    const actual = motor;
    return () => { media?.removeEventListener('change', cambiarMovimiento); actual?.destruir(); };
  });
  $effect(() => { motor?.configurar({modo, pausa:pausada, reducido:quieta}); });

  function salpicar(evento) {
    const caja = agua.getBoundingClientRect();
    motor?.salpicar(evento.detail ? evento.clientX-caja.left : null,
      evento.detail ? evento.clientY-caja.top : null);
  }
</script>

<div class="escena" class:amplia={amplio} data-modo={modo}>
  <button class="agua" type="button" aria-label="Lanzar una fuente de símbolos matemáticos en el agua" disabled={!motor} onclick={salpicar} bind:this={agua}>
    <canvas bind:this={canvas} aria-hidden="true"></canvas>
    {#if !motor}
      <svg class="respaldo" viewBox="0 0 24 24" aria-hidden="true" style:fill={AZUL_DEEPSEEK}><path d={TRAZO_DEEPSEEK} /></svg>
    {/if}
  </button>
  {#if motor && !quieta}
    <button class="pausa" type="button" aria-label={pausada ? 'Reanudar animación' : 'Pausar animación'}
      title={pausada ? 'Reanudar animación' : 'Pausar animación'} aria-pressed={pausada}
      onclick={() => { pausada=!pausada; }}>
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        {#if pausada}<path d="M8 5v14l11-7z" />{:else}<path d="M7 5h3v14H7zM14 5h3v14h-3z" />{/if}
      </svg>
    </button>
  {/if}
  <span class="pista">{quieta || !motor ? 'Escena sin movimiento' : 'Toca el agua para lanzar una fuente'}</span>
</div>

<style>
  .escena { position:relative; min-inline-size:0; }
  .agua {
    position:relative; display:block; inline-size:100%; block-size:clamp(10rem,24vw,13rem);
    padding:0; overflow:hidden; cursor:pointer; border:0; border-radius:var(--radius-trazado);
    background:var(--surface-panel); touch-action:pan-y;
    outline:1px solid var(--trazo); outline-offset:-1px;
  }
  .amplia .agua { block-size:clamp(11rem,26vw,15rem); }
  .agua:focus-visible { outline-offset:-4px; }
  canvas { display:block; inline-size:100%; block-size:100%; max-inline-size:none; pointer-events:none; }
  .respaldo { position:absolute; inset:25% auto auto 40%; inline-size:20%; block-size:50%; }
  .pista { display:block; margin-block-start:.35rem; color:var(--ink-secondary); font-size:var(--texto-xs); }
  .pausa { position:absolute; inset-block-start:4px; inset-inline-end:4px; inline-size:44px; block-size:44px;
    display:grid; place-items:center; padding:0; border:0; background:transparent; color:var(--ink-primary); cursor:pointer; }
  .pausa::before { content:''; position:absolute; inset:9px; border:1px solid var(--trazo); border-radius:50%; background:var(--surface-paper); }
  .pausa svg { position:relative; inline-size:12px; block-size:12px; fill:currentColor; }
  .pausa:hover::before { border-color:var(--accent-main); }
  .pausa:focus-visible { border-radius:50%; }
</style>
