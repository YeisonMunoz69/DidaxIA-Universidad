
<script>
  import { ESPACIO_PROFESIONAL, ESPACIO_TUTOR } from '../../enrutado/espacios.js';

  let {
    activo,
    rotuloProfesional,
    alElegir
  } = $props();

  const OPCIONES = $derived([
    { valor: ESPACIO_TUTOR, rotulo: 'Tutor' },
    { valor: ESPACIO_PROFESIONAL, rotulo: rotuloProfesional }
  ]);
</script>

<div class="selector" role="group" aria-label="Espacio de trabajo">
  {#each OPCIONES as opcion (opcion.valor)}
    <button
      type="button"
      class="opcion"
      class:activa={activo === opcion.valor}
      aria-pressed={activo === opcion.valor}
      onclick={() => alElegir(opcion.valor)}
    >
      <span class="marca" aria-hidden="true"></span>
      <span class="rotulo">{opcion.rotulo}</span>
    </button>
  {/each}
</div>

<style>
  .selector {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 2px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    background: var(--surface-panel);
    box-shadow: var(--shadow-soft);
    flex-shrink: 0;
  }

  .opcion {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.28rem 0.6rem;
    border: 1px solid transparent;
    border-radius: calc(var(--radius-sm) - 2px);
    background: transparent;
    color: var(--ink-secondary);
    font-family: var(--fuente-manuscrita);
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.015em;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .opcion:hover { color: var(--ink-primary); background: var(--surface-paper); }

  .opcion:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 1px;
  }

  .opcion.activa {
    background: var(--accent-surface);
    border-color: var(--accent-main);
    color: var(--accent-main);
  }

  .marca {
    inline-size: 6px;
    block-size: 6px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0;
    transition: var(--transition-fast);
  }

  .opcion.activa .marca { opacity: 1; }

  @media (max-width: 48rem) {
    .opcion {
      min-block-size: 44px;
      padding-inline: 0.7rem;
      font-size: 16px;
    }

    .marca { display: none; }
    .rotulo { min-inline-size: 0; overflow: hidden; text-overflow: ellipsis; }
  }

  @media (prefers-reduced-motion: reduce) {
    .opcion, .marca { transition: none; }
  }
</style>
