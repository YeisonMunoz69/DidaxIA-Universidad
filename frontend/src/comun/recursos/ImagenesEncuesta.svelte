<script>
 import Dialogo from '../base/Dialogo.svelte';
 import Icono from '../base/Icono.svelte';
 let { imagenes=[] }=$props();
 let ampliada=$state(null), abierto=$state(false);
</script>
<div class="evidencias-encuesta">
 {#each imagenes as imagen}
  <figure>
   <button class="ampliar-evidencia" type="button" aria-label={`Ampliar imagen: ${imagen.alt}`} onclick={()=>{ampliada=imagen;abierto=true;}}>
    <img src={imagen.src} alt={imagen.alt} loading="lazy" decoding="async" />
    <span class="indicador-ampliar" aria-hidden="true"><Icono nombre="ampliar" medida={18} /></span>
   </button>
   {#if imagen.pie}<figcaption>{imagen.pie}</figcaption>{/if}
  </figure>
 {/each}
</div>
{#if ampliada}<Dialogo bind:abierto titulo="Imagen del enunciado" tipo="comunicar" ancho="min(96vw, 90rem)">
 <p>{ampliada.alt}</p><img class="ampliada" src={ampliada.src} alt={ampliada.alt} />
 {#if ampliada.pie}<p>{ampliada.pie}</p>{/if}
</Dialogo>{/if}
<style>
 .evidencias-encuesta{display:grid;gap:1rem;margin:1rem 0;min-width:0}figure{margin:0;min-width:0}.evidencias-encuesta button.ampliar-evidencia{display:flex;flex-direction:column;position:relative;box-sizing:border-box;min-width:0;max-width:100%;overflow:hidden;gap:.5rem;width:100%;background:var(--surface-paper);color:var(--ink-primary);border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);padding:.6rem;cursor:zoom-in}button:focus-visible{outline:2px solid var(--accent-main)}img{display:block;max-width:100%;height:auto;margin:auto}button.ampliar-evidencia img{width:auto;max-width:100%;min-width:0;max-height:40rem;object-fit:contain;flex:none}.evidencias-encuesta button.ampliar-evidencia .indicador-ampliar{position:absolute;bottom:.5rem;right:.5rem;display:grid;place-items:center;width:36px;height:36px;box-sizing:border-box;color:var(--accent-main);background:var(--surface-paper);border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);box-shadow:var(--shadow-soft);pointer-events:none}figcaption{font-size:.85rem;line-height:1.5;white-space:pre-wrap;margin-top:.5rem;overflow-wrap:anywhere}.ampliada{max-height:none}
</style>
