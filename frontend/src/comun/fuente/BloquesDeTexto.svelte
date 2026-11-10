
<script>
  import Notacion from '../turno/Notacion.svelte';

  let {
    contenido
  } = $props();

  const bloques = $derived(contenido?.bloques ?? []);

  const CONOCIDOS = [
    'parrafo',
    'encabezado',
    'lista',
    'cita',
    'matematica',
    'tabla',
    'regla'
  ];

  function conocido(tipo) {
    return CONOCIDOS.includes(tipo);
  }

  function etiquetaDeEncabezado(nivel) {
    const n = Math.min(Math.max(Number(nivel) || 3, 3), 6);
    return `h${n}`;
  }
</script>

{#snippet trozos(lista)}
  {#each lista ?? [] as trozo, i (i)}
    {#if trozo.tipo === 'matematica'}
      <Notacion expresion={trozo.texto} />
    {:else if trozo.tipo === 'fuerte'}
      <strong>{trozo.texto}</strong>
    {:else if trozo.tipo === 'enfasis'}
      <em>{trozo.texto}</em>
    {:else if trozo.tipo === 'codigo'}
      <code>{trozo.texto}</code>
    {:else if trozo.tipo === 'enlace'}
      <a href={trozo.destino} target="_blank" rel="noopener noreferrer">
        {trozo.texto}
        <span class="externo" aria-hidden="true">↗</span>
        <span class="solo-lectores"> (se abre en otra pestaña)</span>
      </a>
    {:else}
      {trozo.texto}
    {/if}
  {/each}
{/snippet}

<div class="texto-del-corpus">
  {#each bloques as bloque, indice (indice)}
    {#if bloque.tipo === 'parrafo'}
      <p>{@render trozos(bloque.trozos)}</p>
    {:else if bloque.tipo === 'encabezado'}
      <svelte:element this={etiquetaDeEncabezado(bloque.nivel)}>
        {@render trozos(bloque.trozos)}
      </svelte:element>
    {:else if bloque.tipo === 'matematica'}
      <div class="formula"><Notacion expresion={bloque.latex} bloque /></div>
    {:else if bloque.tipo === 'lista' && bloque.ordenada}
      <ol>
        {#each bloque.elementos as elemento, i (i)}
          <li>{@render trozos(elemento)}</li>
        {/each}
      </ol>
    {:else if bloque.tipo === 'lista'}
      <ul>
        {#each bloque.elementos as elemento, i (i)}
          <li>{@render trozos(elemento)}</li>
        {/each}
      </ul>
    {:else if bloque.tipo === 'cita'}
      <blockquote>{@render trozos(bloque.trozos)}</blockquote>
    {:else if bloque.tipo === 'tabla'}


      <div class="tabla-desplazable" tabindex="0" role="region" aria-label="Tabla del material">
        <table>
          <thead>
            <tr>
              {#each bloque.encabezados as celda, i (i)}
                <th scope="col">{@render trozos(celda)}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each bloque.filas as fila, f (f)}
              <tr>
                {#each fila as celda, c (c)}
                  <td>{@render trozos(celda)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if bloque.tipo === 'regla'}
      <hr />
    {:else if !conocido(bloque.tipo)}

      <p class="desconocido">
        Este material trae una parte que esta versión todavía no sabe mostrar.
      </p>
    {/if}
  {/each}

  {#if contenido?.truncado}
    <p class="aviso">
      El material es muy extenso y aquí se muestra sólo su comienzo.
    </p>
  {/if}
</div>

<style>
  .texto-del-corpus {
    color: var(--ink-primary);
    line-height: 1.65;
    overflow-wrap: anywhere;
    min-width: 0;
  }

  .texto-del-corpus :global(p) {
    margin: 0 0 var(--espacio-md);
  }

  .texto-del-corpus :global(h3),
  .texto-del-corpus :global(h4),
  .texto-del-corpus :global(h5),
  .texto-del-corpus :global(h6) {
    margin: var(--espacio-lg) 0 var(--espacio-sm);
    line-height: 1.3;
  }

  ol,
  ul {
    margin: 0 0 var(--espacio-md);
    padding-inline-start: 1.5em;
  }

  li {
    margin-bottom: var(--espacio-xs);
  }

  blockquote {
    margin: 0 0 var(--espacio-md);
    padding: var(--espacio-sm) var(--espacio-md);
    border-inline-start: 3px solid var(--trazo-suave);
    color: var(--ink-secondary);
  }

  .formula {
    margin: var(--espacio-md) 0;
    overflow-x: auto;
  }

  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.92em;
    background: var(--surface-panel);
    border-radius: var(--radius-xs);
    padding: 0.1em 0.35em;
  }

  hr {
    border: 0;
    border-top: 1px solid var(--trazo-suave);
    margin: var(--espacio-lg) 0;
  }

  .tabla-desplazable {
    overflow-x: auto;
    max-width: 100%;
    margin: 0 0 var(--espacio-md);
    border-radius: var(--radius-sm);
  }

  .tabla-desplazable:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  table {
    border-collapse: collapse;
    min-width: 100%;
    font-size: var(--texto-sm);
  }

  th,
  td {
    border: 1px solid var(--trazo-suave);
    padding: var(--espacio-xs) var(--espacio-sm);
    text-align: start;
    vertical-align: top;
  }

  th {
    background: var(--surface-panel);
  }

  a {
    color: var(--accent-main);
  }

  .externo {
    font-size: 0.85em;
  }

  .desconocido,
  .aviso {
    font-size: var(--texto-sm);
    color: var(--semantic-warning);
    background: var(--semantic-warning-bg);
    padding: var(--espacio-sm) var(--espacio-md);
    border-radius: var(--radius-sm);
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
