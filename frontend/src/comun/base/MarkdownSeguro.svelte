<script>
  import { bloquesMarkdown, fragmentosMarkdown } from '../../nucleo/presentacion/markdownSeguro.js';

  let { texto = '' } = $props();
  const bloques = $derived(bloquesMarkdown(texto));
</script>

{#snippet linea(fragmentos)}
  {#each fragmentos as fragmento}
    {#if fragmento.tipo === 'fuerte'}<strong>{fragmento.valor}</strong>
    {:else if fragmento.tipo === 'fuerte_codigo'}<strong><code>{fragmento.valor}</code></strong>
    {:else if fragmento.tipo === 'codigo'}<code>{fragmento.valor}</code>
    {:else if fragmento.tipo === 'enfasis'}<em>{fragmento.valor}</em>
    {:else}{fragmento.valor}{/if}
  {/each}
{/snippet}

<article class="markdown-seguro">
  {#each bloques as bloque}
    {#if bloque.tipo === 'titulo'}
      {#if bloque.nivel === 1}<h2>{@render linea(bloque.contenido)}</h2>
      {:else if bloque.nivel === 2}<h3>{@render linea(bloque.contenido)}</h3>
      {:else}<h4>{@render linea(bloque.contenido)}</h4>{/if}
    {:else if bloque.tipo === 'parrafo'}
      <p>{@render linea(bloque.contenido)}</p>
    {:else if bloque.tipo === 'lista'}
      {#if bloque.ordenada}
        <ol>{#each bloque.items as item}<li>{@render linea(item)}</li>{/each}</ol>
      {:else}
        <ul>{#each bloque.items as item}<li>{@render linea(item)}</li>{/each}</ul>
      {/if}
    {:else if bloque.tipo === 'tabla'}

      <div class="tabla-desplazable" tabindex="0" role="region" aria-label="Tabla del documento">
        <table>
          <thead><tr>{#each bloque.cabecera as celda}<th scope="col">{@render linea(fragmentosMarkdown(celda))}</th>{/each}</tr></thead>
          <tbody>{#each bloque.filas as fila}<tr>{#each fila as celda}<td>{@render linea(fragmentosMarkdown(celda))}</td>{/each}</tr>{/each}</tbody>
        </table>
      </div>
    {:else if bloque.tipo === 'separador'}
      <hr />
    {/if}
  {/each}
</article>

<style>
  .markdown-seguro { color: var(--ink-primary); line-height: 1.65; }
  h2, h3, h4 { color: var(--ink-primary); line-height: 1.25; }
  h2 { margin: 0 0 1rem; font-size: 1.55rem; }
  h3 { margin: 1.7rem 0 0.55rem; font-size: 1.15rem; }
  h4 { margin: 1.25rem 0 0.4rem; font-size: 1rem; }
  p { margin: 0.6rem 0; }
  ul, ol { margin: 0.6rem 0; padding-inline-start: 1.5rem; }
  li + li { margin-block-start: 0.35rem; }
  code { font-family: var(--fuente-mono); background: var(--surface-panel); padding: 0.1em 0.3em; border-radius: var(--radius-xs); }
  hr { border: 0; border-block-start: 1px solid var(--trazo-suave); margin: 1.5rem 0; }
  .tabla-desplazable { overflow-x: auto; margin: 0.85rem 0; }
  table { border-collapse: collapse; min-inline-size: 34rem; inline-size: 100%; }
  th, td { border: 1px solid var(--trazo-suave); padding: 0.55rem 0.65rem; text-align: start; vertical-align: top; }
  th { background: var(--surface-panel); }
</style>
