
<script>
  import Icono from '../base/Icono.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
</script>

<p class="aviso-profesional" role="note">
  <Icono nombre="escudo" medida={14} />
  <span class="aviso-completo">
    <strong>Consulta profesional.</strong>
    No genera evaluación, diagnóstico, alertas ni indicadores de estudiante.
    Se guarda en tu historial personal.
  </span>
  <span class="aviso-compacto"><strong>Consulta profesional</strong> · historial personal</span>
  <span class="ayuda-aviso"><BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Esta consulta profesional no genera evaluación, diagnóstico, alertas ni indicadores de estudiante. La conversación sí se guarda en tu historial personal." ariaLabel="Alcance de la consulta profesional" /></span>
</p>

<style>
  .aviso-profesional {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: 0;
    padding: 0.4rem 0.9rem;
    max-inline-size: none;
    border-block-end: 1px solid var(--ink-ghost);
    background: var(--surface-panel);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    line-height: 1.4;
  }

  .aviso-profesional strong { color: var(--ink-secondary); font-weight: 600; }

  .aviso-profesional :global(svg) { color: var(--accent-main); flex-shrink: 0; }
  .aviso-compacto, .ayuda-aviso { display: none; }
  @media (min-width: 48.0625rem) {
    .aviso-completo { display: none; }
    .aviso-compacto, .ayuda-aviso { display: inline-flex; align-items: center; }
  }

  @media (max-width: 48rem) {
    .aviso-profesional { padding-inline: 0.75rem; align-items: flex-start; }
    .aviso-profesional :global(svg) { margin-block-start: 2px; }
  }
</style>
