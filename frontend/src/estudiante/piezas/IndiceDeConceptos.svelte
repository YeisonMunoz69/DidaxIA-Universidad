
<script>
  import Icono from '../../comun/base/Icono.svelte';
  import BuscadorDeConceptos from './BuscadorDeConceptos.svelte';
  import ListaDeConceptos from './ListaDeConceptos.svelte';

  let {
    banco = [],
    conceptos = [],
    cargando = false,
    filtro = $bindable(''),
    seleccionada = null,
    temas = [], tema = $bindable('Todos'), visitados = new Set(),
    alAbrir
  } = $props();
</script>

<nav class="panel-indice" aria-label="Banco de conceptos">
  <div class="cabecera-indice">
    <span class="titulo-indice">Contenido</span>
    <span class="badge-total">{banco.length} conceptos</span>
  </div>

  <BuscadorDeConceptos bind:filtro />
  {#if temas.length}<div class="temas" aria-label="Temas de estudio">{#each temas as opcion}<button type="button" aria-pressed={tema === opcion} onclick={() => (tema = opcion)}>{opcion}</button>{/each}</div>{/if}
  <ListaDeConceptos
    {cargando}
    {conceptos}
    {filtro}
    {seleccionada}
    {visitados}
    {alAbrir}
    alLimpiar={() => (filtro = '')} />

  <div class="pie-indice">
    <Icono nombre="escudo" medida={13} />
    <span>Marcas temporales en tu navegador. No se envían al sistema.</span>
  </div>
</nav>

<style>
  .temas{display:flex;gap:.35rem;flex-wrap:wrap;padding:.5rem 0;}
  .temas button{padding:.35rem .65rem;min-height:32px;border:1px solid var(--trazo-suave);border-radius:999px;background:var(--surface-paper);color:var(--ink-secondary);font:inherit;font-size:.7rem;cursor:pointer;}
  .temas button[aria-pressed="true"]{background:var(--accent-surface);border-color:var(--accent-main);color:var(--accent-main);}
  .panel-indice {
    flex: 0 0 17.5rem;
    max-inline-size: none;
    inline-size: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: none;
    block-size: 100%;
    height: 100%;
    min-block-size: 0;
    box-sizing: border-box;
    overflow: hidden;
  }

  .cabecera-indice {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-inline: 2px;
    flex-shrink: 0;
  }

  .titulo-indice {
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--ink-primary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .badge-total {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--ink-secondary);
    background: var(--surface-paper);
    padding: 1px 6px;
    border-radius: var(--radius-pill, 9999px);
    border: 1px solid var(--trazo-suave);
  }

  .pie-indice {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-top: var(--espacio-xs);
    border-top: 1px solid var(--trazo-suave);
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.3;
  }

  @media (max-width: 48rem) {
    .temas{display:flex;gap:.35rem;flex-wrap:wrap;padding:.5rem 0;}
  .temas button{padding:.35rem .65rem;min-height:32px;border:1px solid var(--trazo-suave);border-radius:999px;background:var(--surface-paper);color:var(--ink-secondary);font:inherit;font-size:.7rem;cursor:pointer;}
  .temas button[aria-pressed="true"]{background:var(--accent-surface);border-color:var(--accent-main);color:var(--accent-main);}
  .panel-indice {
      max-block-size: none;
      flex: 1 1 auto;
      inline-size: 100%;
      max-inline-size: 100%;
    }
  }
</style>
