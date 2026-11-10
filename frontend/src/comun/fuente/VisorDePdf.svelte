
<script>
  let {
    fuente,
    titulo,
    paginaInterna = null,
    paginaImpresa = null,
    exacta = true
  } = $props();

  const direccion = $derived(
    paginaInterna ? `${fuente}#page=${paginaInterna}` : fuente
  );

  let visible = $state(true);
</script>

<section class="visor" aria-labelledby="visor-titulo">
  <h3 id="visor-titulo">{titulo}</h3>

  <p class="correspondencia">
    {#if paginaImpresa && paginaInterna}
      Página {exacta ? '' : 'aproximada '}<strong>{paginaImpresa}</strong> de la
      obra impresa · hoja <strong>{paginaInterna}</strong> de este archivo.
      <span class="matiz">
        Las dos cifras no coinciden, y ésa es la razón de mostrarlas juntas.
      </span>
    {:else if paginaImpresa}
      Página {exacta ? '' : 'aproximada '}<strong>{paginaImpresa}</strong> de la
      obra impresa.
      <span class="matiz">
        No hay correspondencia comprobada con las hojas de este archivo, así que
        se abre por el principio en vez de señalar una hoja sin medir.
      </span>
    {:else}
      <span class="matiz">Se abre por el principio del documento.</span>
    {/if}
  </p>

  <div class="acciones">
    <button type="button" onclick={() => (visible = !visible)} aria-expanded={visible}>
      {visible ? 'Ocultar el documento' : 'Mostrar el documento'}
    </button>
    <a href={direccion} target="_blank" rel="noopener noreferrer">
      Abrir en otra pestaña
      <span class="solo-lectores">(el mismo documento)</span>
    </a>
  </div>

  {#if visible}

    <object data={direccion} type="application/pdf" title={titulo}>
      <div class="sin-visor">
        <p>
          Este navegador no puede mostrar el documento aquí dentro.
        </p>
        <p>
          <a href={direccion} target="_blank" rel="noopener noreferrer">
            Abrir el documento en otra pestaña
          </a>
        </p>
      </div>
    </object>
  {/if}
</section>

<style>
  .visor {
    margin-top: var(--espacio-lg);
  }

  h3 {
    font-size: 1rem;
    margin: 0 0 var(--espacio-xs);
  }

  .correspondencia {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    margin: 0 0 var(--espacio-sm);
  }

  .matiz {
    display: block;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .acciones {
    display: flex;
    flex-wrap: wrap;
    gap: var(--espacio-sm);
    align-items: center;
    margin-bottom: var(--espacio-sm);
  }

  .acciones button,
  .acciones a {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    padding: 0 var(--espacio-md);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    background: var(--surface-paper);
    color: var(--ink-primary);
    font: inherit;
    text-decoration: none;
    cursor: pointer;
  }

  .acciones button:focus-visible,
  .acciones a:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  object {
    display: block;
    width: 100%;
    height: min(70vh, 640px);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    background: var(--surface-panel);
  }

  .sin-visor {
    padding: var(--espacio-lg);
    font-size: var(--texto-sm);
  }

  .sin-visor a {
    color: var(--accent-main);
  }

  .solo-lectores {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
