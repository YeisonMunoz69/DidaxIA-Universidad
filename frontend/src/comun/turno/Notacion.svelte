
<script>
  import { getContext } from 'svelte';
  import { copiaDeFormula, CONTEXTO_COPIA_FORMULAS } from './copiaDeFormula.js';
  const copiable = getContext(CONTEXTO_COPIA_FORMULAS) ?? false;
  import { renderizar } from '../../nucleo/formato/notacion.js';

  let {
    expresion = '',
    alternativo = '',
    bloque = false,
    compacto = false,
    agrandar = false
  } = $props();

  const pintada = $derived(renderizar(expresion, { bloque, agrandar }));
  const listo = $derived(Boolean(pintada.html));
  const nombreAccesible = $derived(
    alternativo?.trim() || `Expresión matemática: ${expresion}`
  );
</script>

{#if listo}
  <span class="notacion" class:bloque class:compacto role="math"
        aria-label={nombreAccesible}>

    <span class="formula" use:copiaDeFormula={{habilitada:copiable,expresion}}>{@html pintada.html}</span>
  </span>
{:else}

  <span class="fallo">
    No se pudo mostrar la expresión
    {#if expresion}<code class="crudo">{expresion}</code>{/if}
  </span>
{/if}

<style>
  .notacion {
    font-family: var(--fuente-mono);
    background: var(--surface-panel);
    padding: 0.1em 0.35em;
    border-radius: var(--radius-xs);
  }

  .bloque {
    display: block;
    padding: 0.8em 1em;
    margin-block: 0.6em;
    text-align: center;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-soft);
    overflow-x: auto;
  }

  .bloque.compacto {
    padding: 0.35em 0.6em;
    margin-block: 0.25em;
    font-size: var(--texto-sm);
  }

  .bloque :global(.katex-display) {
    inline-size: max-content;
    min-inline-size: 100%;
    margin: 0;
  }

  .bloque :global(.katex-display > .katex) { white-space: nowrap; }

  .fallo {
    font-size: var(--texto-sm);
    color: var(--semantic-error);
  }

  .crudo {
    font-family: var(--fuente-mono);
    margin-inline-start: 0.4em;
  }
</style>
