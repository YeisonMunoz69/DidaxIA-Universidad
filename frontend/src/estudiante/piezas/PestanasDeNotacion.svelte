<script>
  import { animarPestanaTeclas } from '../../nucleo/animaciones/gsap.js';
  import { CATEGORIAS_DE_NOTACION, TECLAS_ACCION, TECLAS_NAVEGACION } from '../../nucleo/formato/catalogo-de-notacion.js';
  import TeclaDeNotacion from './TeclaDeNotacion.svelte';

  let { alInsertar, alComando } = $props();
  let pestanaActiva = $state(CATEGORIAS_DE_NOTACION[0].id);
  /** @type {HTMLButtonElement[]} */
  let botonesDePestana = $state([]);

  $effect(() => {
    pestanaActiva;
    if (typeof document === 'undefined') return;
    const panel = document.getElementById(`panel-${pestanaActiva}`);
    if (panel) animarPestanaTeclas(panel);
  });

  /** @param {KeyboardEvent} evento */
  function alTeclearEnPestanas(evento) {
    const indice = CATEGORIAS_DE_NOTACION.findIndex((c) => c.id === pestanaActiva);
    let siguiente = null;
    if (evento.key === 'ArrowRight') siguiente = (indice + 1) % CATEGORIAS_DE_NOTACION.length;
    else if (evento.key === 'ArrowLeft') siguiente = (indice - 1 + CATEGORIAS_DE_NOTACION.length) % CATEGORIAS_DE_NOTACION.length;
    else if (evento.key === 'Home') siguiente = 0;
    else if (evento.key === 'End') siguiente = CATEGORIAS_DE_NOTACION.length - 1;
    if (siguiente === null) return;
    evento.preventDefault();
    pestanaActiva = CATEGORIAS_DE_NOTACION[siguiente].id;
    botonesDePestana[siguiente]?.focus();
  }

  function teclasDe(categoria) {
    if (categoria.id !== 'numeros') return categoria.teclas;
    // En el teclado numérico esas acciones ocupaban una quinta columna
    // intercalada; ahora la misma columna persiste al cambiar de pestaña.
    return categoria.teclas.filter((tecla) =>
      !['deleteBackward', 'moveToPreviousChar', 'moveToNextChar'].includes(tecla.comando)
      && !['\\div', '\\times', '-', '+'].includes(tecla.inserta)
    );
  }
</script>

<div class="teclado-avanzado">
  <div
    class="pestanas"
    role="tablist"
    aria-label="Categorías de símbolos"
    aria-orientation="horizontal"
    tabindex="-1"
    onkeydown={alTeclearEnPestanas}
  >
    {#each CATEGORIAS_DE_NOTACION as categoria, indice (categoria.id)}
      <button
        type="button"
        role="tab"
        id="pestana-{categoria.id}"
        aria-controls="panel-{categoria.id}"
        aria-selected={pestanaActiva === categoria.id}
        tabindex={pestanaActiva === categoria.id ? 0 : -1}
        bind:this={botonesDePestana[indice]}
        onclick={() => (pestanaActiva = categoria.id)}
      >
        {categoria.nombre}
      </button>
    {/each}
  </div>

  {#each CATEGORIAS_DE_NOTACION as categoria (categoria.id)}
    <div
      class="panel"
      role="tabpanel"
      id="panel-{categoria.id}"
      aria-labelledby="pestana-{categoria.id}"
      tabindex="0"
      hidden={pestanaActiva !== categoria.id}
    >
      <div class="navegacion-cursor" role="group" aria-label="Mover el cursor">
        {#each TECLAS_NAVEGACION as tecla (tecla.comando)}
          <TeclaDeNotacion {...tecla} {alInsertar} {alComando} />
        {/each}
      </div>
      <div class="cuerpo-teclado">
        <div class="rejilla-avanzada" class:numerica={categoria.id === 'numeros'}>
          {#each teclasDe(categoria) as tecla (tecla.inserta ?? tecla.comando)}
            <TeclaDeNotacion {...tecla} {alInsertar} {alComando} />
          {/each}
        </div>
        <div class="acciones-persistentes" role="group" aria-label="Operaciones y borrado">
          {#each TECLAS_ACCION as tecla (tecla.nombre)}
            <TeclaDeNotacion {...tecla} {alInsertar} {alComando} />
          {/each}
        </div>
      </div>
    </div>
  {/each}
</div>

<style>
  .teclado-avanzado {
    display: flex;
    flex-direction: column;
    gap: 0;
    min-inline-size: 0;
  }

  .pestanas {
    display: flex;
    flex-wrap: nowrap;
    gap: 3px;
    padding: 3px;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    overflow-x: auto;
    scrollbar-width: thin;
  }

  .pestanas [role='tab'] {
    flex: 1 0 auto;
    padding: 5px 8px;
    border: 1px solid transparent;
    border-radius: var(--radius-xs);
    background: transparent;
    color: var(--ink-secondary);
    font-family: inherit;
    font-size: 11px;
    font-weight: 500;
    text-align: center;
    white-space: nowrap;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .pestanas [role='tab']:hover:not([aria-selected='true']) {
    background: var(--surface-canvas);
    color: var(--ink-primary);
    transform: translateY(-1px);
  }

  .pestanas [role='tab'][aria-selected='true'] {
    background: var(--surface-paper);
    border-color: var(--trazo-suave);
    color: var(--accent-main);
    font-weight: 600;
    box-shadow: var(--shadow-soft);
  }

  .panel {
    max-block-size: min(13rem, calc(var(--alto-visible, 100dvh) * .34));
    padding: 8px;
    overflow-y: auto;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-block-start: none;
    border-end-start-radius: var(--radius-sm);
    border-end-end-radius: var(--radius-sm);
  }

  .navegacion-cursor {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .35rem;
    margin-block-end: .35rem;
  }

  .cuerpo-teclado {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(42px, 3rem);
    gap: .35rem;
    min-inline-size: 0;
  }

  .acciones-persistentes { display: grid; grid-template-columns: minmax(0, 1fr); gap: .35rem; align-content: start; }

  .rejilla-avanzada {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    gap: 0.35rem;
    align-content: start;
    grid-auto-rows: minmax(44px, auto);
  }

  .rejilla-avanzada.numerica {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  @media (max-width: 48rem), (pointer: coarse) and (max-width: 75rem) {
    .pestanas [role='tab'] {
      min-block-size: 44px;
      padding-inline: 10px;
    }

    .panel {
      max-block-size: min(17rem, calc(var(--alto-visible, 100dvh) * .26));
      padding: 6px;
    }

    .rejilla-avanzada {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 4px;
    }
    .navegacion-cursor, .acciones-persistentes { gap: 4px; }
  }

  @media (max-height: 32rem) and (pointer: coarse) {
    .panel { max-block-size: calc(var(--alto-visible, 100dvh) * .26); }
  }
</style>
