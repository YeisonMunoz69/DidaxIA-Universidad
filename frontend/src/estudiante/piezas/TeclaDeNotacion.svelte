<script>
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import { renderizar } from '../../nucleo/formato/notacion.js';

  let {
    muestra,
    vista,
    inserta,
    comando,
    nombre,
    alInsertar,
    alComando
  } = $props();

  const expresionDeMuestra = $derived(
    (vista ?? inserta)?.replaceAll('\\placeholder{}', '\\square') ?? ''
  );
  const formula = $derived(comando ? null : renderizar(expresionDeMuestra, { bloque: false }));
</script>

<button use:ayudaContextual
  type="button"
  class="tecla"
  title={nombre}
  aria-label={nombre}
  onpointerdown={(evento) => evento.preventDefault()}
  onclick={() => comando ? alComando?.(comando) : alInsertar?.(`$${inserta}$`)}
>
  <span class="formula-tecla" aria-hidden="true">
    {#if formula?.html}
      {@html formula.html}
    {:else}
      {muestra}
    {/if}
  </span>
</button>

<style>
  .tecla {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    min-inline-size: 2.2rem;
    min-block-size: 44px;
    padding: 5px 8px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo);
    border-radius: var(--radius-xs);
    color: var(--ink-primary);
    font-family: var(--fuente-mono);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: var(--shadow-soft);
    transition: background-color 0.15s ease, border-color 0.15s ease,
      color 0.15s ease, transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 0.2s ease;
    white-space: nowrap;
  }

  span {
    display: inline-block;
    white-space: nowrap;
    word-break: keep-all;
  }

  .formula-tecla :global(.katex) {
    font-size: 1.05em;
  }

  .tecla:hover {
    background: var(--accent-surface);
    border-color: var(--accent-main);
    color: var(--accent-main);
    transform: translateY(-2px) scale(1.04);
    box-shadow: 0 4px 12px var(--accent-glow);
  }

  .tecla:active {
    transform: translateY(0) scale(0.94);
    box-shadow: var(--shadow-soft);
  }

  @media (max-width: 75rem) {
    .tecla {
      min-inline-size: 0;
      padding-inline: 0.28em;
      font-size: var(--texto-xs);
    }
  }
</style>
