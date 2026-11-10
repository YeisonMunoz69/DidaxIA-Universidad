
<script>
  import { getContext } from 'svelte';
  import { copiaDeFormula, CONTEXTO_COPIA_FORMULAS } from './copiaDeFormula.js';
  const copiable = getContext(CONTEXTO_COPIA_FORMULAS) ?? false;
  import { renderizar, trozos } from '../../nucleo/formato/notacion.js';

  let {
    contenido = '',
    enLinea = false
  } = $props();

  const partes = $derived(
    trozos(contenido).map((p) =>
      p.tipo === 'formula' ? { ...p, ...renderizar(p.valor, { agrandar: true }) } : p
    )
  );
</script>

{#snippet pintar()}
  {#each partes as p, i (i)}
    {#if p.tipo === 'texto'}
      {p.valor}
    {:else if p.tipo === 'enfasis'}
      <strong>{p.valor}</strong>
    {:else if p.tipo === 'matiz'}
      <em>{p.valor}</em>
    {:else if p.tipo === 'codigo'}
      <code>{p.valor}</code>
    {:else if p.html}
      <span class="formula-en-prosa" role="math" aria-label={p.valor}><span
        use:copiaDeFormula={{habilitada:copiable,expresion:p.valor}}>{@html p.html}</span></span>
    {:else}
      <code class="formula-cruda">{p.valor}</code>
    {/if}
  {/each}
{/snippet}

{#if enLinea}
  <span>{@render pintar()}</span>
{:else}
  <p>{@render pintar()}</p>
{/if}

<style>
  p {
    inline-size: 100%;
    max-inline-size: none;
    margin: 0;
  }

  .formula-en-prosa {
    display: inline-block;
    vertical-align: middle;
    padding: 0.1em 0.45em;
    margin: 0 0.18em;
    background: var(--accent-surface);
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-xs);
    color: var(--accent-main);
    font-size: 1.02em;
    font-weight: 500;
    transition: var(--transition-fast);
  }

  .formula-en-prosa:hover {
    background: var(--accent-surface-hover);
    box-shadow: 0 2px 8px var(--accent-glow);
    transform: translateY(-1px);
  }

  .formula-en-prosa :global(.katex) {
    color: var(--accent-main);
  }

  :global(body.dark-theme) :global(.estudiante) .formula-en-prosa {
    background: var(--accent-glow);
    border-color: var(--accent-main);
    color: inherit;
  }

  :global(body.dark-theme) :global(.estudiante) .formula-en-prosa :global(.katex) {
    color: inherit;
  }

  code {
    font-family: var(--fuente-mono);
    font-size: 0.9em;
    padding: 0.1em 0.3em;
    background: var(--surface-panel);
    border-radius: var(--radius-xs);
  }
</style>
