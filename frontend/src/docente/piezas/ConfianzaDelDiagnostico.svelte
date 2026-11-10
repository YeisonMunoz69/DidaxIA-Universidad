
<script>
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  let {
    valor = null,
    observaciones = null
  } = $props();

  const nivel = $derived(
    valor == null ? null
    : valor < 0.4 ? { clase: 'debil',       texto: 'indicio débil' }
    : valor < 0.7 ? { clase: 'moderado',    texto: 'indicio moderado' }
    :               { clase: 'consistente', texto: 'indicios consistentes' }
  );
</script>

{#if nivel}
  <p class="confianza {nivel.clase}">
    <span class="punto" aria-hidden="true"></span>
    <strong>{nivel.texto}</strong>
    <span class="dato">({(valor * 100).toFixed(0)} %{observaciones
      ? ` · ${observaciones} observaciones` : ''})</span>
  </p>
{:else}

  <p class="confianza sin-dato">
    <span class="punto" aria-hidden="true"></span>
    <strong>Sin medida de confianza</strong>
    {#if observaciones != null}<span class="dato">{observaciones} mensajes analizables</span>{/if}
    <BotonAyudaTooltip tamano="sm" ariaLabel="Por qué no hay medida de confianza" texto="Estos indicios todavía no están calibrados. El número de mensajes indica la evidencia analizable; no demuestra precisión del instrumento ni permite un diagnóstico." />
  </p>
{/if}

<style>
  .confianza {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.4em;
    margin: 0;
    inline-size: fit-content;
    max-inline-size: 100%;
    padding: 0.35em 0.7em;
    border-radius: var(--radius-pill, 9999px);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    font-size: var(--texto-sm);
  }

  .punto {
    align-self: center;
    inline-size: 6px;
    block-size: 6px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
  }

  .dato { font-size: var(--texto-xs); color: var(--ink-tertiary); }

  .debil       { color: var(--ink-tertiary); }
  .moderado    { color: var(--ink-secondary); }
  .consistente { color: var(--ink-primary); border-color: var(--accent-main); }
  .sin-dato    { color: var(--semantic-warning); border-color: var(--semantic-warning); }
</style>
