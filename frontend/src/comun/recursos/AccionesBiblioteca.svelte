<script>
  import { onMount } from 'svelte';
  import Icono from '../base/Icono.svelte';
  let { titulo, children, esquina = false } = $props();
  let abierto = $state(true);
  let raiz, panel;
  let posicion = $state('');
  function cerrar() { abierto=false;if(raiz)raiz.open=false; }
  function cerrarFuera(evento) { if (esquina && raiz?.open && !raiz.contains(evento.target)) cerrar(); }
  function cerrarTrasAccion(evento) { if(esquina&&panel?.contains(evento.target)&&evento.target.closest('button'))cerrar(); }
  function ubicar() {
    if (!esquina || !raiz?.open || !panel) return;
    const rect=raiz.getBoundingClientRect(), altura=panel.getBoundingClientRect().height;
    const ancho=Math.min(280,innerWidth-24), izquierda=Math.max(12,Math.min(rect.right-ancho,innerWidth-ancho-12));
    const arriba=rect.bottom+6+altura<=innerHeight-12 ? rect.bottom+6 : Math.max(12,rect.top-altura-6);
    posicion=`left:${izquierda}px;top:${arriba}px;width:${ancho}px;max-height:${innerHeight-24}px`;
  }
  onMount(() => {
    if (esquina) { abierto=false;window.addEventListener('click',cerrarTrasAccion);return()=>window.removeEventListener('click',cerrarTrasAccion); }
    const telefono = matchMedia('(max-width: 650px)');
    const ajustar = () => abierto = !telefono.matches;
    ajustar(); telefono.addEventListener('change', ajustar);
    return () => telefono.removeEventListener('change', ajustar);
  });
</script>
<svelte:window onpointerdown={cerrarFuera} onkeydown={e=>{if(esquina&&raiz?.open&&e.key==='Escape'){cerrar();raiz.querySelector('summary')?.focus();}}} onresize={()=>{if(esquina)cerrar();}} />
<details bind:this={raiz} class="acciones-biblioteca" class:esquina bind:open={abierto} ontoggle={ubicar} onfocusout={e=>{if(esquina&&!raiz?.contains(e.relatedTarget))cerrar();}}>
  <summary aria-label={`Más acciones para ${titulo}`} aria-haspopup="true">{#if esquina}<Icono nombre="mas-vertical" medida={20} />{:else}<Icono nombre="mas" /><span>Más acciones</span><Icono nombre="bajar" medida={16} />{/if}</summary>
  <div bind:this={panel} class="acciones secundarias" style={esquina?posicion:undefined} role="group" aria-label={`Acciones de ${titulo}`}>{@render children?.()}</div>
</details>
<style>
  summary { display:none; }
  .esquina { position:absolute;right:12px;top:12px; }
  .esquina summary { display:grid;place-items:center;width:44px;height:44px;cursor:pointer;list-style:none;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);background:var(--surface-paper);color:var(--ink-primary); }
  .esquina summary::-webkit-details-marker { display:none; }
  .esquina summary:focus-visible { outline:2px solid var(--accent-main);outline-offset:2px; }
  .esquina:not([open])>.secundarias { display:none!important; }
  .esquina :global(.secundarias) { position:fixed;z-index:30;display:grid;grid-template-columns:1fr;gap:4px;overflow:auto;margin:0;padding:8px;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);background:var(--surface-paper);box-shadow:var(--shadow-soft); }
  .esquina :global(.secundarias button) { justify-content:flex-start;text-align:left;width:100%;border:0;min-height:44px;background:transparent;color:var(--ink-primary); }
  .esquina :global(.secundarias button:hover) { background:var(--accent-surface); }
  @media(max-width:650px) {
    .acciones-biblioteca:not(.esquina) { border-top:1px solid var(--trazo-suave); margin-top:12px; }
    summary { display:flex; align-items:center; gap:8px; min-height:44px; font-size:.85rem; cursor:pointer; list-style:none; }
    summary span { flex:1; }
    summary::-webkit-details-marker { display:none; }
    summary:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; }
    .acciones-biblioteca:not(.esquina) :global(.secundarias) { display:grid; grid-template-columns:1fr; gap:8px; margin:8px 0 0; }
    .acciones-biblioteca :global(button) { justify-content:flex-start; text-align:left; }
  }
</style>
