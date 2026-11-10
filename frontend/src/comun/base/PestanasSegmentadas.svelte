<script>
  import Icono from './Icono.svelte';

  let { opciones = [], activa, alElegir, etiqueta, prefijo } = $props();

  function navegar(evento, id) {
    const actual = opciones.findIndex((opcion) => opcion.id === id);
    let siguiente = actual;
    if (evento.key === 'ArrowRight') siguiente = (actual + 1) % opciones.length;
    else if (evento.key === 'ArrowLeft') siguiente = (actual - 1 + opciones.length) % opciones.length;
    else if (evento.key === 'Home') siguiente = 0;
    else if (evento.key === 'End') siguiente = opciones.length - 1;
    else return;
    evento.preventDefault();
    alElegir(opciones[siguiente].id);
    document.getElementById(`${prefijo}-pestana-${opciones[siguiente].id}`)?.focus();
  }
</script>

<nav class="contenedor" aria-label={etiqueta}>
  <div class="desplazamiento">
    <div class="riel" role="tablist" aria-label={etiqueta}>
      {#each opciones as opcion (opcion.id)}
        <button
          id={`${prefijo}-pestana-${opcion.id}`}
          type="button"
          role="tab"
          aria-selected={activa === opcion.id}
          aria-controls={`${prefijo}-panel-${opcion.id}`}
          tabindex={activa === opcion.id ? 0 : -1}
          class:activa={activa === opcion.id}
          onclick={() => alElegir(opcion.id)}
          onkeydown={(evento) => navegar(evento, opcion.id)}>
          <Icono nombre={opcion.icono} medida={16} />
          <span>{opcion.titulo}</span>
        </button>
      {/each}
    </div>
  </div>
</nav>

<style>
  .contenedor { inline-size: 100%; min-inline-size: 0; margin-block: 1.25rem 1.5rem; }
  .desplazamiento { inline-size: max-content; max-inline-size: min(36.25rem, 100%); margin-inline: auto; overflow-x: auto; overscroll-behavior-inline: contain; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
  .desplazamiento::-webkit-scrollbar { display: none; }
  .riel { display: inline-flex; align-items: center; gap: .25rem; min-inline-size: max-content; padding: .25rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-pill); background: var(--surface-panel); box-shadow: var(--shadow-soft); }
  button { display: inline-flex; align-items: center; justify-content: center; gap: .4rem; flex: none; min-block-size: 2.75rem; padding: .5rem .8rem; border: 1px solid transparent; border-radius: var(--radius-pill); background: transparent; color: var(--ink-tertiary); font: inherit; font-size: var(--texto-sm); font-weight: 650; white-space: nowrap; cursor: pointer; transition: var(--transition-fast); }
  button:hover:not(.activa) { background: var(--surface-canvas); color: var(--ink-primary); }
  button.activa { border-color: var(--trazo-suave); background: var(--surface-paper); color: var(--ink-primary); font-weight: 750; box-shadow: var(--shadow-soft); }
  button:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 2px; }
  :global(body.dark-theme) button.activa { border-color: var(--trazo); }
  @media (prefers-reduced-motion: reduce) { button { transition: none; } }
</style>
