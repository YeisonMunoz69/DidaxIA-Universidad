
<script>
  import { onDestroy } from 'svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import * as conceptos from '../../nucleo/api/conceptos.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { coincideConConsulta } from '../../nucleo/busqueda/conceptos.js';
  import { cacheDeLectura } from '../../nucleo/lectura/cache.js';
  import { temaDeConcepto } from '../../nucleo/lectura/conceptos.js';
  import { lectura } from '../../nucleo/lectura/lectura.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';
  import IndiceDeConceptos from '../piezas/IndiceDeConceptos.svelte';
  import PanelDeDetalleDeConcepto from '../piezas/PanelDeDetalleDeConcepto.svelte';
  let banco = $state([]), abierta = $state(null), cargando = $state(true), fallo = $state(null);
  let filtro = $state(''), tema = $state('Todos'), preparando = $state(false), visitados = $state(new Set());
  let peticion = 0, destruida = false, indice, pendiente = null;
  const cache = cacheDeLectura(conceptos.ficha);
  visitados = new Set(cache.consultados);
  let movil = $state(globalThis.matchMedia?.('(max-width: 47.999rem)').matches ?? false);
  const orden = new Intl.Collator('es', { sensitivity: 'base' });
  const ordenado = $derived([...banco].sort((a, b) => orden.compare(a.nombre, b.nombre)));
  const temas = $derived(['Todos', ...new Set(ordenado.map(temaDeConcepto))]);
  const filtrados = $derived(ordenado.filter(c => coincideConConsulta(c, filtro) && (tema === 'Todos' || temaDeConcepto(c) === tema)));
  const indiceActual = $derived(abierta ? ordenado.findIndex(c => c.id === abierta.id) : -1);
  const anterior = $derived(ordenado[indiceActual - 1]);
  const siguiente = $derived(indiceActual >= 0 ? ordenado[indiceActual + 1] : null);
  onDestroy(() => { destruida = true; peticion++; lectura.inmersiva = false; });
  $effect(() => {
      const m = globalThis.matchMedia?.('(max-width: 47.999rem)');
      const actualizar = () => { if (indice?.matches(':modal'))
          indice.close(); movil = Boolean(m?.matches); };
      m?.addEventListener?.('change', actualizar);
      return () => m?.removeEventListener?.('change', actualizar);
  });
  $effect(() => { lectura.inmersiva = movil && Boolean(abierta); });
  async function cargar() {
      cargando = true;
      fallo = null;
      pendiente = null;
      try {
          const datos = await conceptos.listar();
          if (!destruida)
              banco = datos;
      }
      catch (error) {
          if (!destruida)
              fallo = describir(error);
      }
      finally {
          if (!destruida)
              cargando = false;
      }
  }
  function abrir(id) {
      const actual = ++peticion;
      fallo = null;
      preparando = true;
      pendiente = id;
      function aceptar(ficha) {
          if (destruida || actual !== peticion)
              return false;
          abierta = ficha;
          preparando = false;
          pendiente = null;
          cache.consultados.add(id);
          visitados = new Set(cache.consultados);
          const i = ordenado.findIndex(c => c.id === id);
          for (const c of [ordenado[i - 1], ordenado[i + 1]])
              if (c)
                  cache.precargar(c.id);
          if (movil && indice?.matches(':modal'))
              indice.close();
          return true;
      }
      const guardada = cache.ver(id);
      if (guardada)
          return Promise.resolve(aceptar(guardada));
      return cache.pedir(id).then(aceptar, error => {
          if (destruida || actual !== peticion)
              return false;
          preparando = false;
          fallo = describir(error);
          return false;
      });
  }
  function abrirIndice() { if (movil && abierta)
      indice?.showModal?.(); }
  function alTeclarIndice(evento) {
      if (evento.key === 'Escape' && indice?.matches(':modal')) {
          evento.preventDefault();
          indice.close();
      }
  }
  function volverAlCatalogo() { peticion++; abierta = null; preparando = false; indice?.close?.(); }
  $effect(() => { cargar(); });
</script>

<div class="vista-conceptos" class:leyendo={Boolean(abierta)}>
  <header class="cabecera-conceptos">
    {#if movil&&abierta}
      <button type="button" class="abrir-indice" aria-label="Ver índice de conceptos" onclick={abrirIndice}>☷</button>
      <div class="titulo-movil"><strong>{abierta.nombre}</strong><span>Concepto {indiceActual+1} de {ordenado.length}</span></div>
      <button type="button" aria-label="Volver a la conversación" onclick={()=>navegar('/')}>↙</button>
    {:else}
      <div><span class="subtitulo-modulo">Cuaderno de estudio</span><h1>Conceptos</h1></div>
      <p class="privacidad">Tu lectura es privada · sin registro de consultas</p>
    {/if}
  </header>
  {#if fallo}<Degradacion respuesta={fallo} alReintentar={()=>pendiente?abrir(pendiente):cargar()} />{/if}
  <div class="layout-conceptos" class:con-detalle={Boolean(abierta)}>
    <dialog class="indice-conceptos" class:cajon={movil&&Boolean(abierta)} bind:this={indice} open={!movil||!abierta} aria-label="Índice de conceptos" onkeydown={alTeclarIndice}>
      {#if movil&&abierta}<header class="cabecera-cajon"><span class="tirador" aria-hidden="true"></span><h2>Tu índice de estudio</h2><button type="button" aria-label="Cerrar índice de conceptos" onclick={()=>indice.close()}>×</button></header>{/if}
      <IndiceDeConceptos banco={ordenado} conceptos={filtrados} {cargando} bind:filtro {temas} bind:tema {visitados} seleccionada={abierta?.id} alAbrir={abrir} />
      {#if movil&&abierta}<button type="button" class="volver-catalogo" onclick={volverAlCatalogo}>Ver el catálogo de conceptos</button>{/if}
    </dialog>
    <div class="zona-detalle">
      {#if preparando}<p class="preparando" role="status">Preparando el concepto…</p>{/if}
      <PanelDeDetalleDeConcepto mostrarControles={!movil} banco={filtrados} {abierta} {cargando} {anterior} {siguiente} pagina={Math.max(1,indiceActual+1)} total={ordenado.length} alAbrir={abrir} />
      {#if !movil&&abierta}<button type="button" class="volver-al-indice" onclick={volverAlCatalogo}>Volver al índice de conceptos</button>{/if}
    </div>
  </div>
</div>
<style>
  .vista-conceptos {
    position:relative;
    display:flex;
    flex-direction:column;
    gap:1rem;
    padding:clamp(.7rem,1.5vw,1.5rem);
    inline-size:100%;
    block-size:100%;
    min-block-size:0;
    box-sizing:border-box;
    overflow:hidden;
    background:var(--surface-canvas);
  }
  .cabecera-conceptos {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    flex-shrink:0;
  }
  .subtitulo-modulo {
    color:var(--accent-main);
    font:700 .65rem/1.4 var(--fuente-mono);
    letter-spacing:.14em;
    text-transform:uppercase;
  }
  h1 {
    margin:.15rem 0 0;
    font:700 1.8rem/1.2 Georgia,serif;
    color:var(--ink-primary);
  }
  .privacidad {
    font-size:.75rem;
    color:var(--ink-tertiary);
  }
  .layout-conceptos {
    display:grid;
    grid-template-columns:minmax(15rem,19rem) minmax(0,1fr);
    gap:1.1rem;
    flex:1;
    min-height:0;
  }
  .indice-conceptos {
    position:relative;
    inset:auto;
    margin:0;
    padding:0;
    border:0;
    background:transparent;
    color:var(--ink-primary);
    width:100%;
    height:100%;
    min-height:0;
    overflow:hidden;
    box-sizing:border-box;
  }
  .zona-detalle {
    display:flex;
    flex-direction:column;
    position:relative;
    min-width:0;
    min-height:0;
  }
  .volver-al-indice,.volver-catalogo {
    min-height:32px;
    flex-shrink:0;
    border:0;
    background:transparent;
    color:var(--accent-main);
    font:inherit;
    font-size:.75rem;
    cursor:pointer;
  }
  .preparando {
    position:absolute;
    z-index:45;
    inset:auto 1rem 3rem;
    padding:.5rem 1rem;
    background:var(--surface-panel);
    border:1px solid var(--trazo);
    border-radius:.5rem;
    font-size:.8rem;
  }
  @media(max-width:47.999rem) {
    .vista-conceptos {
      padding:0;
      gap:0;
    }
    .layout-conceptos {
      display:flex;
      flex-direction:column;
      gap:0;
    }
    .zona-detalle {
      flex:1;
    }
    .vista-conceptos:not(.leyendo) .zona-detalle {
      display:none;
    }
    .vista-conceptos.leyendo .cabecera-conceptos { position:absolute; inset:0 0 auto; z-index:40; }
    .vista-conceptos.leyendo :global(.cabecera-detalle) { padding-block-start:calc(44px + 1.3rem); }
    .cabecera-conceptos {
      padding:0 .5rem;
      min-height:44px;
      box-sizing:border-box;
      background:color-mix(in srgb,var(--surface-paper) 86%,transparent);
      backdrop-filter:blur(16px);
      border-bottom:1px solid var(--trazo-suave);
    }
    .privacidad {
      max-width:10rem;
      font-size:.65rem;
    }
    .cabecera-conceptos button {
      flex:0 0 44px;
      min-height:44px;
      border:0;
      border-radius:50%;
      background:transparent;
      color:var(--accent-main);
      font-size:1.25rem;
      cursor:pointer;
    }
    .titulo-movil {
      min-width:0;
      flex:1;
      display:flex;
      flex-direction:column;
      gap:.15rem;
    }
    .titulo-movil strong {
      font:600 .9rem/1.25 Georgia,serif;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .titulo-movil span {
      font:.65rem/1.2 var(--fuente-mono);
      color:var(--ink-tertiary);
    }
    .indice-conceptos {
      flex:1;
    }
    .indice-conceptos.cajon {
      position:absolute;
      inset:auto 0 0;
      max-height:78dvh;
      height:78dvh;
      max-width:100%;
      width:100%;
      border-radius:1.4rem 1.4rem 0 0;
      background:var(--surface-paper);
      box-shadow:0 -16px 60px var(--book-cover-shadow);
    }
    .cajon[open] {
      display:flex;
      flex-direction:column;
      animation:entrar-cajon .3s cubic-bezier(.22,.75,.2,1);
    }
    .cajon::backdrop {
      background:var(--velo-modal);
      backdrop-filter:blur(6px);
    }
    .cajon :global(.panel-indice) {
      flex:1;
      block-size:auto;
      border:0;
      border-radius:0;
    }
    .cabecera-cajon {
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding:1rem;
      position:relative;
    }
    .cabecera-cajon h2 {
      margin:0;
      font:600 1.2rem/1.3 Georgia,serif;
    }
    .cabecera-cajon button {
      width:44px;
      height:44px;
      border:0;
      background:transparent;
      color:inherit;
      font-size:1.6rem;
    }
    .tirador {
      position:absolute;
      top:.4rem;
      left:calc(50% - 1.2rem);
      width:2.4rem;
      height:4px;
      background:var(--trazo);
      border-radius:5px;
    }
    .volver-catalogo { min-height:44px; flex-shrink:0; border:0; background:var(--book-paper); color:var(--accent-main); }
  }
  @keyframes entrar-cajon {
    from {
      transform:translateY(70%);
      opacity:.5;
    }
    to {
      transform:translateY(0);
      opacity:1;
    }
  }
  @media(prefers-reduced-motion:reduce) {
    .cajon[open] {
      animation:none;
    }
  }
</style>
