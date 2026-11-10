
<script>
  import Icono from '../../comun/base/Icono.svelte';
  import { PAGINAS } from '../rutas.js';
  import { ENLACE_AL_TUTOR } from '../../nucleo/configuracion/origenes.js';
  import { MARCA, ICONO_PALETA_PINCEL_SVG } from '../contenido/proyecto.js';
  import InterruptorDeTema from '../../comun/preferencias/InterruptorDeTema.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import SelectorDeColor from '../../comun/preferencias/SelectorDeColor.svelte';
  import { COLOR_INICIAL } from '../../nucleo/preferencias/colores.js';
  import { ejecutarTransicionCircularDeTema } from '../../nucleo/preferencias/transicionDeTema.js';

  let {
    actual = '/',
    temaOscuro = false,
    colores = COLOR_INICIAL,
    alElegirColores = () => {},
    alElegirTema = () => {}
  } = $props();
  let colorAbierto = $state(false);
</script>

<header class="cabecera">
  <a class="marca" href="/" aria-label="{MARCA} · inicio">
    <Icono nombre="didaxia" medida={26} />
    <span class="nombre">{MARCA}</span>
  </a>

  <nav aria-label="Páginas del sitio">
    <ul>
      {#each PAGINAS as pagina (pagina.camino)}
        <li>
          <a
            href={pagina.camino}
            aria-current={pagina.camino === actual ? 'page' : undefined}
            class:vigente={pagina.camino === actual}
          >{pagina.titulo}</a>
        </li>
      {/each}
    </ul>
  </nav>

  <div class="acciones">
    <button class="elegir-color" type="button" aria-label="Elegir color de la portada" onclick={() => colorAbierto=true}>
      <svg class="icono-paleta" viewBox="0 0 500 650" aria-hidden="true" focusable="false">
        {@html ICONO_PALETA_PINCEL_SVG}
      </svg>
    </button>
    <InterruptorDeTema oscuro={temaOscuro} alCambiar={(nuevoTema, evento) => {
      ejecutarTransicionCircularDeTema(evento, nuevoTema, () => {
        alElegirTema(nuevoTema);
      });
    }} />
    <a class="entrar entrada-tutor" href={ENLACE_AL_TUTOR}>
      <Icono nombre="conversacion" medida={15} />
      <span>Entrar al tutor</span>
    </a>
  </div>
</header>
{#if colorAbierto}
<Dialogo bind:abierto={colorAbierto} titulo="Color de la portada" ancho="44rem" class="colores-publicos">
  <SelectorDeColor valor={colores} alElegir={alElegirColores} oscuro={temaOscuro} />
  <p class="nota-local">Esta elección se guarda en este navegador. Tu tutor conserva los ajustes de tu cuenta.</p>
</Dialogo>
{/if}

<style>
  .cabecera {
    position: sticky;
    inset-block-start: 3px;
    z-index: 90;
    flex-shrink: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--espacio-md) var(--espacio-lg);
    padding: var(--espacio-md) var(--espacio-lg);
    background: color-mix(in srgb, var(--surface-panel) 94%, transparent);
    backdrop-filter: blur(14px) saturate(1.08);
    -webkit-backdrop-filter: blur(14px) saturate(1.08);
    border-block-end: 1px solid var(--trazo-suave);
  }

  .marca {
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-sm);
    color: var(--ink-primary);
    text-decoration: none;
    min-block-size: 24px;
  }

  .nombre {
    font-family: var(--fuente-manuscrita);
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1;
    color: var(--ink-primary);
  }

  nav {
    flex: 1;
    min-inline-size: 0;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: var(--espacio-sm) var(--espacio-lg);
  }

  li { max-inline-size: none; }

  nav a {
    display: inline-flex;
    align-items: center;
    min-block-size: 24px;
    font-size: var(--texto-sm);
    font-weight: 500;
    color: var(--ink-secondary);
    text-decoration: none;
    border-block-end: 2px solid transparent;
  }

  nav a:hover { color: var(--accent-main); }

  nav a.vigente {
    color: var(--accent-main);
    border-block-end-color: var(--accent-main);
  }

  .entrar {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-sm);
    padding: 0.5em 1.05em;
    min-block-size: 24px;
    background: var(--accent-main);
    color: var(--surface-paper);
    font-size: var(--texto-sm);
    font-weight: 600;
    text-decoration: none;
    border-radius: var(--radius-trazado);
    box-shadow: 2px 3px 0 color-mix(in srgb, var(--accent-main) 30%, transparent);
    transition: background var(--transition-fast), box-shadow var(--transition-fast);
  }
  .entrar::after {
    content: '';
    position: absolute;
    inset: 2px;
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--surface-paper) 38%, transparent);
    border-radius: inherit;
    pointer-events: none;
    opacity: .4;
    transition: opacity var(--transition-fast);
  }
  .entrar:focus-visible { outline: 2px solid var(--help-color); outline-offset: 3px; }
  .entrar:hover::after, .entrar:focus-visible::after { opacity: 1; }
  @media (prefers-reduced-motion: reduce) { .entrar { animation: none; } .entrar, .entrar::after { transition: none; } }
  .acciones { display: inline-flex; align-items: center; gap: var(--espacio-sm); }
  .elegir-color {
    position: relative;
    display: grid;
    place-items: center;
    min-inline-size: 44px;
    min-block-size: 44px;
    padding: 0;
    border: 0;
    color: var(--ink-primary);
    background: transparent;
    cursor: pointer;
  }
  .elegir-color:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
    border-radius: 50%;
  }
  .icono-paleta {
    position: relative;
    inline-size: 18px;
    block-size: 24px;
    display: block;
    overflow: visible;
    pointer-events: none;
  }
  .nota-local { font-size: var(--texto-xs); margin-block-start: 1rem; color: var(--ink-secondary); }
  :global(dialog.colores-publicos) { max-block-size:calc(100dvh - 2rem); overflow:auto; }
  @media(max-width:48rem) { .entrar { padding:.4em .5em; } .entrar :global(svg) { display:none; } .acciones { gap:.25rem; } }

  .entrar:hover {
    background: var(--accent-hover);
    color: var(--surface-paper);
    box-shadow: var(--shadow-soft);
  }

  @media (max-width: 48rem) {
    .cabecera {
      display: grid;
      grid-template-columns: 1fr auto;
      grid-template-areas:
        "marca acciones"
        "nav nav";
      align-items: center;
      row-gap: var(--espacio-xs);
      column-gap: var(--espacio-sm);
      padding: var(--espacio-sm) var(--espacio-md);
    }

    .marca {
      grid-area: marca;
      min-block-size: 32px;
    }

    .acciones {
      grid-area: acciones;
    }

    .entrar {
      margin: 0;
      padding: 0.4em 0.85em;
      font-size: var(--texto-xs);
    }

    nav {
      grid-area: nav;
      inline-size: 100%;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }

    nav::-webkit-scrollbar {
      display: none;
    }

    ul {
      flex-wrap: nowrap;
      gap: var(--espacio-md);
      padding-block-start: 2px;
      padding-block-end: 2px;
    }

    nav a {
      white-space: nowrap;
      font-size: var(--texto-xs);
    }
  }
</style>
