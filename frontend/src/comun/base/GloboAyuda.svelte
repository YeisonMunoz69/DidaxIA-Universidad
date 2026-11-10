<script>
  import Dialogo from './Dialogo.svelte';
  let { texto, id, movil = false, interactiva = false, caja, obtenerCaja, alCerrar } = $props();
  let abierto = $state(true);
  let globo = $state(null);
  let izquierda = $state(16);
  let arriba = $state(16);
  export function reubicar() {
    if (!globo || movil) return;
    const referencia = obtenerCaja?.() ?? caja;
    const ancho = globo.offsetWidth;
    const alto = globo.offsetHeight;
    izquierda = Math.max(12, Math.min(window.innerWidth - ancho - 12, referencia.left + referencia.width / 2 - ancho / 2));
    arriba = referencia.top > alto + 16 ? referencia.top - alto - 8 : Math.min(window.innerHeight - alto - 12, referencia.bottom + 8);
  }
  $effect(reubicar);
  $effect(() => { if (!abierto) alCerrar(); });
</script>
{#if movil}
  <Dialogo bind:abierto titulo="Ayuda" ancho="24rem"><p class="contenido">{texto}</p></Dialogo>
{:else}
  <div bind:this={globo} class="globo-ayuda" class:solo-etiqueta={!interactiva} role="tooltip" {id}
    style:left={`${izquierda}px`} style:top={`${arriba}px`}>{texto}</div>
{/if}
<style>
  .globo-ayuda { position: fixed; z-index: 1000; inline-size: max-content; max-inline-size: min(22rem, calc(100vw - 1.5rem)); padding: .7rem .85rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-sm); background: var(--surface-paper); box-shadow: var(--shadow-float); color: var(--ink-primary); font-size: var(--texto-xs); line-height: 1.5; overflow-wrap: anywhere; white-space: normal; text-align: start; animation: aparecer .22s cubic-bezier(.34,1.56,.64,1); }
  .solo-etiqueta { pointer-events: none; }
  .globo-ayuda:not(.solo-etiqueta) { max-block-size:calc(100dvh - 2rem);overflow:auto; }
  .contenido { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.55; overflow-wrap: anywhere; }
  @keyframes aparecer { from { opacity: 0; transform: translateY(3px) scale(.98); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .globo-ayuda { animation: none; } }
</style>
