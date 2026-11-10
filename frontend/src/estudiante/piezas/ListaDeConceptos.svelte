
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';

  let {
    cargando = false,
    conceptos = [],
    filtro = '',
    seleccionada = null,
    visitados = new Set(),
    alAbrir,
    alLimpiar
  } = $props();
</script>

{#if cargando}
  <CargadorCubo mensaje="Cargando el banco de conceptos…" />
{:else if conceptos.length}
  <ul class="lista-conceptos">
    {#each conceptos as concepto, indice (concepto.id)}
      <li>
        <button
          type="button"
          class="boton-concepto"
          class:activa={seleccionada === concepto.id}
          aria-current={seleccionada === concepto.id ? 'true' : undefined}
          onclick={() => alAbrir(concepto.id)}>
          <span class="numero-lectura" aria-hidden="true">{String(indice + 1).padStart(2, '0')}</span>
          <span class="nombre">{concepto.nombre}</span>
          <span class="indicador" aria-hidden="true">{visitados.has(concepto.id) ? '✓' : '›'}</span>
          <span class="solo-lectores">{visitados.has(concepto.id) ? ' Consultado en esta visita' : ' Pendiente de lectura'}</span>
        </button>
      </li>
    {/each}
  </ul>
{:else if filtro}
  <div class="estado-sin-resultados">
    <p>No se encontraron conceptos para <em>«{filtro}»</em>.</p>
    <button type="button" class="btn-restaurar-filtro" onclick={alLimpiar}>
      Ver todos los conceptos
    </button>
  </div>
{:else}
  <p class="estado-vacio">El banco está vacío.</p>
{/if}

<style>
  .solo-lectores { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .lista-conceptos {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin: 0;
    padding: 0;
    list-style: none;
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    padding-inline-end: 2px;
  }

  .boton-concepto {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-xs);
    inline-size: 100%;
    padding: 11px 9px;
    min-height: 48px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    font: inherit;
    text-align: start;
    cursor: pointer;
    color: var(--ink-secondary);
    transition: var(--transition);
  }

  .boton-concepto:hover {
    background: var(--surface-canvas);
    border-color: var(--trazo);
    color: var(--ink-primary);
    transform: translateX(2px);
  }

  .boton-concepto.activa {
    background: var(--surface-paper);
    border: 1.5px solid var(--accent-main);
    color: var(--accent-main);
    font-weight: 600;
    box-shadow: var(--shadow-soft);
  }

  .boton-concepto.activa .nombre {
    color: var(--accent-main);
    font-weight: 700;
  }

  .nombre {
    flex: 1;
    min-inline-size: 0;
    font-size: var(--texto-sm);
    font-weight: 500;
    color: var(--ink-primary);
    line-height: 1.35;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: normal;
  }

  .numero-lectura {
    font-variant-numeric: tabular-nums;
    font-size: 0.66rem;
    color: var(--ink-tertiary);
    letter-spacing: 0.05em;
  }

  .indicador {
    font-size: 1.1rem;
    color: var(--ink-tertiary);
    transition: transform 0.16s ease;
  }

  .boton-concepto:hover .indicador,
  .boton-concepto.activa .indicador {
    color: var(--accent-main);
    transform: translateX(2px);
  }

  .estado-vacio {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: var(--espacio-xl) var(--espacio-md);
    color: var(--ink-tertiary);
    font-size: var(--texto-sm);
  }

  .estado-sin-resultados {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 8px;
    padding: var(--espacio-lg) var(--espacio-md);
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .btn-restaurar-filtro {
    background: transparent;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-xs);
    padding: 4px 8px;
    font-family: inherit;
    font-size: var(--texto-xs);
    color: var(--accent-main);
    cursor: pointer;
  }

  .btn-restaurar-filtro:hover { background: var(--surface-canvas); }

  @media (max-width: 48rem) {
    .lista-conceptos { max-block-size: none; }
  }
</style>
