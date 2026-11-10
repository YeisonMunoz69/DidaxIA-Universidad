<script>
  import { tick } from 'svelte';
  import { PALETAS, PARTES_COLOR, configuracionDe, normalizarColores, tokensDeColor } from '../../nucleo/preferencias/colores.js';
  let { valor, alElegir, oscuro=false, activo=true } = $props();
  let editando = $state('claro');
  let carrusel = $state(null);
  let raiz = $state(null);
  let abierta = $state(null);
  let personalizacion;
  $effect(() => { if(!activo) { if(personalizacion) personalizacion.open=false; abierta=null; } });
  const modo = $derived(editando==='oscuro' ? 'Oscuro' : 'Claro');
  const elegidas = $derived(normalizarColores(valor));
  const tokens = $derived(tokensDeColor(elegidas,editando==='oscuro'));
  const tonos = $derived(PALETAS.map(p => ({...p, tokens:tokensDeColor(configuracionDe(p.id),editando==='oscuro')})));
  $effect(() => {
    if(!abierta) return;
    const fuera=e => { if(!raiz?.contains(e.target) || !e.target.closest('.menu-tonos')) abierta=null; };
    document.addEventListener('click',fuera);
    return () => document.removeEventListener('click',fuera);
  });
  function cambiar(parte,familia) { alElegir(normalizarColores({...elegidas,[parte+modo]:familia})); }
  async function abrir(parte,evento) {
    evento.preventDefault();
    abierta = abierta===parte ? null : parte;
    if (abierta) {
      await tick();
      raiz?.querySelector(`[data-parte="${parte}"] [aria-checked="true"]`)?.focus();
    }
  }
  function cerrar(parte) {
    abierta=null;
    raiz?.querySelector(`[data-parte="${parte}"] summary`)?.focus();
  }
  function teclado(evento,parte,indice) {
    if(evento.key==='Escape') { evento.preventDefault(); evento.stopPropagation(); cerrar(parte); return; }
    const desplazamiento={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1};
    if(evento.key in desplazamiento || evento.key==='Home' || evento.key==='End') {
      evento.preventDefault();
      const siguiente=evento.key==='Home' ? 0 : evento.key==='End' ? tonos.length-1 : (indice+desplazamiento[evento.key]+tonos.length)%tonos.length;
      cambiar(parte,tonos[siguiente].id);
      const botones=raiz.querySelectorAll(`[data-parte="${parte}"] [role="radio"]`);
      botones.forEach((b,i)=>b.tabIndex=i===siguiente ? 0 : -1);
      botones[siguiente]?.focus();
    }
  }
  function desplazar(direccion) { carrusel?.scrollBy({left:direccion*carrusel.clientWidth*.8,behavior:globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); }
</script>

<section class="colores" aria-label="Combinaciones de color" bind:this={raiz}>
  <div class="introduccion"><h3>Tu combinación de colores</h3><p>Empieza con una combinación. Después mezcla sus tonos para cada parte del acento.</p></div>
  <div class="cabecera-catalogo">
    <strong>26 combinaciones preestablecidas</strong>
    <div class="pasar"><button type="button" aria-label="Combinaciones anteriores" onclick={() => desplazar(-1)}>←</button><button type="button" aria-label="Más combinaciones" onclick={() => desplazar(1)}>→</button></div>
  </div>
  <div class="catalogo" bind:this={carrusel} role="group" aria-label="Combinaciones preestablecidas">
    {#each PALETAS as p (p.id)}
      <button type="button" class="muestra" aria-label={p.nombre} aria-pressed={JSON.stringify(elegidas)===JSON.stringify(configuracionDe(p.id))}
        onclick={() => alElegir(configuracionDe(p.id))}>
        <span class="duo" aria-hidden="true" style:--muestra-a={oscuro ? p.acentoOscuro : p.acentoClaro} style:--muestra-b={oscuro ? p.contrasteOscuro : p.contrasteClaro}></span>
        <span>{p.nombre}</span><small>Claro y oscuro</small>
      </button>
    {/each}
  </div>
  <details class="personalizacion" bind:this={personalizacion} ontoggle={e => { if(!e.currentTarget.open) abierta=null; }}>
  <summary>Combinar tonos del catálogo<span aria-hidden="true">⌄</span></summary>
  <div class="personalizar" role="group" aria-label="Combinar tonos del catálogo">
    <div class="modos" role="group" aria-label="Modo que quieres personalizar">
      <button type="button" aria-pressed={editando==='claro'} onclick={() => {editando='claro';abierta=null;}}>Colores de claro</button>
      <button type="button" aria-pressed={editando==='oscuro'} onclick={() => {editando='oscuro';abierta=null;}}>Colores de oscuro</button>
    </div>
    <p class="orientacion">Puedes usar vinotinto en los botones, lino en las superficies y grafito en los detalles. Cada modo conserva su mezcla.</p>
    <div class="campos">
      {#each PARTES_COLOR as parte (parte.id)}
        <div class="campo">
          <span class="rotulo">{parte.nombre}</span>
          <details class="menu-tonos" data-parte={parte.id} open={abierta===parte.id}
            onfocusout={e => { if(e.relatedTarget && !e.currentTarget.contains(e.relatedTarget)) abierta=null; }}>
            <summary tabindex="0" aria-label={`${parte.nombre} para modo ${editando}`} onclick={e => abrir(parte.id,e)}>
              <span class="tono elegido" aria-hidden="true" style:background={tokens[parte.token]}></span>
              <span>{PALETAS.find(p=>p.id===elegidas[parte.id+modo])?.nombre}</span><span aria-hidden="true">⌄</span>
            </summary>
            {#if abierta===parte.id}<div class="lista-tonos" role="radiogroup" aria-label={`Tonos de ${parte.nombre} para modo ${editando}`}>
              {#each tonos as p,i (p.id)}
                <button type="button" role="radio" aria-label={p.nombre} aria-checked={elegidas[parte.id+modo]===p.id}
                  tabindex={elegidas[parte.id+modo]===p.id ? 0 : -1}
                  onkeydown={e=>teclado(e,parte.id,i)} onclick={() => {cambiar(parte.id,p.id);cerrar(parte.id);}}>
                  <span class="tono opcion" aria-hidden="true" style:background={p.tokens[parte.token]}></span>
                  <span>{p.nombre}</span>
                  {#if elegidas[parte.id+modo]===p.id}<span class="marca" aria-hidden="true">✓</span>{/if}
                </button>
              {/each}
            </div>{/if}
          </details>
          <small>{parte.uso}</small>
        </div>
      {/each}
    </div>
    <div class="miniatura" style:--papel-preview={tokens['--surface-paper']} style:--tinta-preview={tokens['--ink-primary']} style:--acento-preview={tokens['--accent-main']} style:--contraste-preview={tokens['--decorative-contrast']} style:--hover-preview={tokens['--accent-hover']} style:--superficie-preview={tokens['--accent-surface']} style:--gradiente-preview={tokens['--accent-gradient']}>
      <span class="halo uno"></span><span class="halo dos"></span><strong>Un espacio para comprender</strong><span>Dos colores que se encuentran.</span>
      <div class="ejemplos"><span class="boton-preview" style:color={tokens['--accent-on-main']}>Continuar</span><span class="superficie-preview" style:color={tokens['--accent-light']}>Selección</span><span class="gradiente-preview" aria-label="Muestra del degradado"></span></div>
    </div>
    <details class="valores"><summary>Ver las variables de esta combinación</summary>
      <dl>{#each PARTES_COLOR as parte}<div><dt>{parte.token}</dt><dd>{tokens[parte.token]}</dd></div>{/each}</dl>
    </details>
  </div>
  </details>
  <p class="nota">Se usan tonos del catálogo y se ajusta el contraste para conservar la lectura. Las confirmaciones, ayudas, errores y advertencias mantienen sus colores.</p>
</section>

<style>
  .colores { display:grid; gap:1rem; min-inline-size:0; }
  h3,p { margin:0; } h3 { font-size:var(--texto-md); } p { font-size:var(--texto-sm); color:var(--ink-secondary); line-height:1.5; }
  .introduccion { display:grid; gap:.4rem; }
  .cabecera-catalogo { display:flex; align-items:center; justify-content:space-between; gap:.75rem; font-size:var(--texto-sm); }
  .pasar { display:flex; gap:.35rem; } .pasar button { inline-size:44px; }
  .catalogo { display:flex; gap:.65rem; overflow-x:auto; padding:.3rem; scroll-snap-type:x mandatory; scrollbar-width:thin; }
  button { font:inherit; cursor:pointer; color:var(--ink-primary); background:var(--surface-paper); border:1px solid var(--trazo); border-radius:var(--radius-sm); min-block-size:44px; }
  .muestra { display:grid; justify-items:center; align-content:center; gap:.5rem; text-align:center; padding:.85rem; font-size:var(--texto-xs); flex:0 0 8.7rem; scroll-snap-align:start; }
  button[aria-pressed=true] { outline:2px solid var(--accent-main); outline-offset:1px; background:var(--accent-surface); font-weight:750; }
  .duo { inline-size:2.6rem; block-size:2.6rem; border-radius:50%; background:linear-gradient(135deg,var(--muestra-a) 50%,var(--muestra-b) 50%); border:1px solid var(--trazo-suave); }
  .personalizacion { border:1px solid var(--trazo-suave); border-radius:var(--radius-md); min-inline-size:0; }
  .personalizacion > summary { display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.4rem .85rem; list-style:none; font-weight:750; font-size:var(--texto-sm); box-sizing:border-box; }
  .personalizacion > summary::-webkit-details-marker { display:none; }
  .personalizacion[open] > summary span { transform:rotate(180deg); }
  .personalizacion > summary:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; border-radius:inherit; }
  .personalizar { display:grid; gap:1rem; padding:.85rem; min-inline-size:0; }
  .modos { display:flex; gap:.5rem; } .modos button { flex:1; padding:.5rem; font-size:var(--texto-xs); }
  .orientacion,.nota { font-size:var(--texto-xs); }
  .campos { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; } .campo { display:grid; align-content:start; gap:.35rem; font-size:var(--texto-xs); min-inline-size:0; }
  .rotulo { display:flex; align-items:center; justify-content:space-between; gap:.35rem; font-weight:750; }
  .tono { flex:none; border:1px solid var(--trazo); border-radius:var(--radius-sm); }
  .elegido { inline-size:2rem; block-size:1.65rem; }
  .menu-tonos { border:1px solid var(--trazo); border-radius:var(--radius-sm); background:var(--surface-paper); }
  .menu-tonos summary { display:flex; align-items:center; gap:.55rem; padding:.5rem; min-block-size:44px; box-sizing:border-box; list-style:none; color:var(--ink-primary); }
  .menu-tonos summary::-webkit-details-marker { display:none; }
  .menu-tonos summary span:nth-child(2) { flex:1; min-inline-size:0; }
  .lista-tonos { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.45rem; padding:.55rem; max-block-size:19rem; overflow-y:auto; overscroll-behavior:contain; scrollbar-width:thin; animation:mostrar-tonos .15s ease-out; }
  .lista-tonos button { position:relative; display:grid; justify-items:center; align-content:start; gap:.4rem; padding:.55rem .3rem; min-inline-size:0; text-align:center; font-size:var(--texto-xs); }
  .opcion { inline-size:100%; block-size:2rem; box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink-primary) 8%,transparent); }
  .lista-tonos button[aria-checked=true] { outline:2px solid var(--accent-main); outline-offset:-2px; font-weight:750; }
  .marca { position:absolute; top:.7rem; right:.5rem; background:var(--surface-paper); color:var(--ink-primary); border-radius:50%; inline-size:1.3rem; }
  @keyframes mostrar-tonos { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:none; } }
  @media (prefers-reduced-motion:reduce) { .lista-tonos { animation:none; } }
  :global(html[data-animaciones='no']) .lista-tonos { animation:none; }
  small { color:var(--ink-secondary); font-size:var(--texto-xs); }
  .miniatura { position:relative; overflow:hidden; display:grid; gap:.45rem; justify-items:center; padding:1.5rem .75rem; border-radius:var(--radius-md); color:var(--tinta-preview); background:var(--papel-preview); isolation:isolate; font-size:var(--texto-sm); text-align:center; }
  .halo { position:absolute; z-index:-1; inline-size:80%; block-size:150%; border-radius:50%; filter:blur(25px); opacity:.25; top:-20%; } .uno { left:-6%; background:var(--acento-preview); } .dos { right:-6%; background:var(--contraste-preview); }
  .ejemplos { display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:.6rem; }
  .boton-preview { padding:.4rem .8rem; background:var(--acento-preview); border-radius:var(--radius-sm); font-weight:700; } .boton-preview:hover { background:var(--hover-preview); }
  .superficie-preview { background:var(--superficie-preview); padding:.4rem .8rem; border-radius:var(--radius-sm); }
  .gradiente-preview { inline-size:4.5rem; block-size:1.5rem; background:var(--gradiente-preview); border-radius:var(--radius-sm); }
  .valores { font-size:var(--texto-xs); } summary { cursor:pointer; min-block-size:44px; align-content:center; } dl { display:grid; gap:.5rem; margin:.5rem 0 0; } dt { font-family:var(--fuente-mono); } dd { margin:.2rem 0 0; overflow-wrap:anywhere; color:var(--ink-secondary); }
  @media(max-width:25rem) { .campos { grid-template-columns:1fr; } }
  @media(prefers-reduced-motion:reduce) { .catalogo { scroll-behavior:auto; } }
</style>
