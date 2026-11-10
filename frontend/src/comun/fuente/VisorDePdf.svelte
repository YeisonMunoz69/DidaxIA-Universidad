<!--
El PDF de una parte o de una obra, con su correspondencia de páginas.

LA PÁGINA A LA QUE SALTA NO ES LA QUE CITA EL FRAGMENTO
--------------------------------------------------------
Y decirlo es media pieza. Un fragmento cita la **página impresa** —la que
llevaría escrita el libro en papel— y el archivo tiene sus propias hojas. En un
PDF dividido nunca coinciden: la parte empieza en su hoja 1 mientras la obra va
por la 146. En el PDF completo sólo se salta cuando el catálogo conserva un
desfase medido; `PIS` no ofrece ejemplar completo y por eso no lo necesita.

Por eso este componente muestra las dos cifras y, cuando no hay correspondencia
comprobada, **no ofrece el salto**: abrir una hoja cualquiera y presentarla como
la página citada sería inventar el dato que la fase prohíbe inventar.

EL FALLBACK ES HONESTO, NO UN SEGUNDO VISOR
---------------------------------------------
Si el navegador no sabe mostrar un PDF —o lo bloquea— el contenido alternativo
del `<object>` ofrece **abrir el mismo recurso autorizado** en otra pestaña. No
descarga otra cosa, no propone un espejo y no dice «inténtelo más tarde»: el
enlace apunta a la misma dirección que el visor no pudo pintar.



-->
<script>
  let {
    /** La dirección del PDF. La compone `nucleo/api/fuentes.js`. */
    fuente,
    /** Rótulo humano de lo que se está viendo. */
    titulo,
    /** Hoja del archivo a la que abrir, o `null` si no se sabe. */
    paginaInterna = null,
    /** Página impresa que cita el fragmento, para poder contrastarlas. */
    paginaImpresa = null,
    /** `false` cuando la página impresa es un rango y no un punto. */
    exacta = true
  } = $props();

  /**
   * `#page=N` es la convención que entienden los visores integrados de los
   * navegadores. Va **al final y sólo si hay número comprobado**: sin él, el
   * documento se abre por el principio, que es honesto.
   */
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
    <!-- `<object>` y no `<iframe>`: el contenido alternativo de un `object` se
         pinta cuando el navegador no sabe mostrar el tipo, que es justo el caso
         que hay que cubrir. Un `iframe` sin visor deja un rectángulo en blanco
         y nadie sabe qué pasó. -->
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
    /* Alto suficiente para leer y no tanto como para que en un teléfono el
       documento se coma la pantalla entera y no se pueda salir de él. */
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
