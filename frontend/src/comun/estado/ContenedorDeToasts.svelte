<script>
  import Icono from '../base/Icono.svelte';
  import { toast } from './toasts.svelte.js';
  const iconos = { descarga:'descargar', confirmar:'check', 'cerrar-sesion':'cerrar', eliminar:'eliminar', comunicar:'correo' };
</script>

<div class="avisos" role="status" aria-live="polite" aria-atomic="false">
  {#each toast.avisos as aviso (aviso.id)}
    <div class="aviso" class:descarga={aviso.tipo === 'descarga'} class:confirmar={aviso.tipo === 'confirmar'} class:salida={aviso.tipo === 'cerrar-sesion'} class:eliminar={aviso.tipo === 'eliminar'} class:comunicar={aviso.tipo === 'comunicar'}>
      <Icono nombre={iconos[aviso.tipo]} medida={20} /><span>{aviso.mensaje}</span>
    </div>
  {/each}
</div>

<style>
  .avisos { position:fixed; z-index:10000; inset-block-start:max(1rem,env(safe-area-inset-top)); inset-inline-start:50%; transform:translateX(-50%); inline-size:max-content; max-inline-size:calc(100vw - 2rem); display:grid; gap:.55rem; pointer-events:none; }
  .aviso { --tono:var(--semantic-info); display:flex; align-items:center; gap:.65rem; inline-size:max-content; max-inline-size:100%; box-sizing:border-box; min-inline-size:0; min-block-size:3rem; padding:.65rem .9rem; border:2px solid var(--ink-primary); border-radius:255px 15px 225px 15px/15px 225px 15px 255px; background:var(--surface-elevated); color:var(--ink-primary); box-shadow:3px 4px 0 var(--ink-primary); animation:entrar .2s ease-out, salir .25s ease-in 3.25s forwards; font-size:var(--texto-sm); font-weight:650; overflow-wrap:anywhere; }
  .aviso span { min-inline-size:0; }
  .aviso :global(svg) { flex:none; color:var(--tono); }
  .descarga { --tono:var(--color-sky); } .confirmar { --tono:var(--semantic-success); } .salida { --tono:var(--semantic-warning); } .eliminar { --tono:var(--semantic-error); } .comunicar { --tono:var(--color-violet); }
  @keyframes entrar { from { opacity:0; transform:translateY(-.8rem); } to { opacity:1; transform:translateY(0); } }
  @keyframes salir { to { opacity:0; transform:translateY(-.5rem); } }
  @media(max-width:48rem) { .avisos { inline-size:calc(100vw - 2rem); grid-template-columns:minmax(0,1fr); } .aviso { inline-size:100%; } }
  @media(prefers-reduced-motion:reduce) { .aviso { animation:none; } }
</style>
