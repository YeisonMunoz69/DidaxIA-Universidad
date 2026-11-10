
<script>
  import "./entrada-tutor.css";
  import SaltarAlContenido from '../comun/base/SaltarAlContenido.svelte';
  import CabeceraPublica from './piezas/CabeceraPublica.svelte';
  import PiePublico from './piezas/PiePublico.svelte';
  import BarraDesplazamiento from './piezas/BarraDesplazamiento.svelte';
  import AmbienteMatematico from './piezas/AmbienteMatematico.svelte';
  import PantallaNoEncontrada from '../comun/base/PantallaNoEncontrada.svelte';
  import { normalizar, paginaDe } from './rutas.js';
  import { guardarTema, leerTema } from '../nucleo/preferencias/tema.js';
  import { aplicarColores, leerColoresPublicos, guardarColoresPublicos, PALETAS, configuracionDe } from '../nucleo/preferencias/colores.js';

  let {
    camino = globalThis.location?.pathname ?? '/'
  } = $props();

  const actual = $derived(normalizar(camino));
  const pagina = $derived(paginaDe(actual));
  let elementoDesplazable = $state(null);
  let scrollProgreso = $state(0);
  let tema = $state(leerTema());
  let colores = $state(inicializarColores());
  function inicializarColores() {
    if (normalizar(camino) !== '/') return leerColoresPublicos();
    const elegida = configuracionDe(PALETAS[Math.floor(Math.random() * PALETAS.length)].id);
    guardarColoresPublicos(elegida);
    return elegida;
  }
  let sistemaOscuro = $state(
    globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  );
  const temaOscuro = $derived(
    tema === 'oscuro' || (tema === 'sistema' && sistemaOscuro)
  );

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
    const alCambiar = () => { sistemaOscuro = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  $effect(() => {
    globalThis.document?.body?.classList.toggle('dark-theme', temaOscuro);
    globalThis.document?.documentElement?.classList.toggle('dark-theme', temaOscuro);
    aplicarColores(colores,temaOscuro);
  });

  function alDesplazar() {
    if (!elementoDesplazable) return;
    const maxScroll = elementoDesplazable.scrollHeight - elementoDesplazable.clientHeight;
    scrollProgreso = maxScroll > 0
      ? Math.min(1, Math.max(0, elementoDesplazable.scrollTop / maxScroll))
      : 0;
  }
</script>

<SaltarAlContenido />

<div
  bind:this={elementoDesplazable}
  class="desplazable"
  onscroll={alDesplazar}
>

  <div
    class="barra-progreso-scroll"
    style:transform="scaleX({scrollProgreso})"
    aria-hidden="true"
  ></div>


  <BarraDesplazamiento contenedor={elementoDesplazable} />

  <AmbienteMatematico />

  <CabeceraPublica actual={pagina ? actual : ''} {temaOscuro}
    {colores} alElegirColores={c => { colores=c; guardarColoresPublicos(c); }}
    alElegirTema={(nuevo) => { tema = nuevo; guardarTema(nuevo); }} />

  <main id="contenido">
    {#if actual === '/'}
      {#if pagina}
        {@const Pagina = pagina.componente}
        <Pagina {temaOscuro} {colores} />
      {/if}
    {:else}
      <div class="columna">
        {#if pagina}
          {@const Pagina = pagina.componente}
          <Pagina />
        {:else}

          <PantallaNoEncontrada camino={actual} />
        {/if}
      </div>
    {/if}
  </main>

  <PiePublico />
</div>

<style>
  .desplazable {
    position: relative;
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    inline-size: 100%;
    display: flex;
    flex-direction: column;
    background: var(--surface-canvas);
    isolation: isolate;
    scrollbar-width: none;
  }

  .desplazable::-webkit-scrollbar {
    display: none;
    inline-size: 0;
    block-size: 0;
  }

  .barra-progreso-scroll {
    position: sticky;
    top: 0;
    left: 0;
    inline-size: 100%;
    block-size: 3px;
    background: var(--accent-gradient);
    transform-origin: 0% 50%;
    z-index: 100;
    pointer-events: none;
    transition: transform 0.08s ease-out;
  }

  main,
  :global(.pie) {
    position: relative;
    z-index: 1;
  }

  main {
    flex: 1;
    inline-size: 100%;
  }

  .columna {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-2xl);
    inline-size: 100%;
    max-inline-size: min(82rem, 100%);
    margin-inline: auto;
    padding: var(--espacio-2xl) var(--espacio-lg);
  }


  @media (max-width: 48rem) {
    .columna {
      gap: var(--espacio-xl);
      padding: var(--espacio-xl) var(--espacio-md);
    }
  }
</style>
