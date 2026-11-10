
<script>
  import { getContext } from 'svelte';
  import { copiaDeFormula, CONTEXTO_COPIA_FORMULAS } from './copiaDeFormula.js';
  const copiable = getContext(CONTEXTO_COPIA_FORMULAS) ?? false;
  import { renderizar } from '../../nucleo/formato/notacion.js';

  let { expresion = '', alternativo = '', rotulado = true } = $props();

  const pintada = $derived(renderizar(expresion, { bloque: false, agrandar: true }));
</script>

<span
  class="citada"
  role="math"
  aria-label={alternativo || undefined}
>{#if rotulado}<span class="rotulo">solo mencionado</span>{/if}{#if pintada.html}<span class="formula" aria-hidden={!copiable} use:copiaDeFormula={{habilitada:copiable,expresion}}>{@html pintada.html}</span><span class="sr-only">{expresion}</span>{:else}<span class="expresion">{expresion}</span>{/if}</span>

<style>
  .citada {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35em;
    padding: 0.1em 0.45em;
    background: var(--accent-surface);
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-xs);
    color: var(--accent-main);
  }

  .rotulo {
    font-size: var(--texto-xs);
    color: var(--accent-main);
    font-weight: 600;
  }

  .formula {
    display: inline-block;
    vertical-align: middle;
  }

  .formula :global(.katex) {
    color: var(--accent-main);
  }

  .expresion {
    font-family: var(--fuente-mono);
  }

  .sr-only {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
