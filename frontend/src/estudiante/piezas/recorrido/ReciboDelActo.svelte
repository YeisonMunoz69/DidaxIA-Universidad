
<script>
  import { ayudaContextual } from '../../../comun/base/ayudaContextual.js';
  import Icono from '../../../comun/base/Icono.svelte';

  let {
    recibo,
    titulo = 'Quedó registrado'
  } = $props();

  const DECISION = {
    otorgado: 'Autorizaste',
    rechazado: 'No autorizaste',
    revocado: 'Retiraste tu autorización'
  };

  const ALCANCE = {
    titular: 'Consentimiento del titular',
    asentimiento: 'Tu asentimiento',
    representante: 'Autorización del representante'
  };

  function comoFecha(iso) {
    if (!iso) return '';
    const fecha = new Date(iso);
    if (Number.isNaN(fecha.getTime())) return iso;
    return fecha.toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
  }
</script>

{#if recibo}
  <section class="recibo" role="status" aria-labelledby="recibo-titulo">
    <div class="cabecera">
      <span class="sello"><Icono nombre="check" medida={16} /></span>
      <h3 id="recibo-titulo">{titulo}</h3>
    </div>

    <dl class="campos">
      {#if recibo.decision}
        <div class="campo">
          <dt>Decisión</dt>
          <dd>{DECISION[recibo.decision] ?? recibo.decision}</dd>
        </div>
      {/if}
      {#if recibo.alcance}
        <div class="campo">
          <dt>Documento</dt>
          <dd>{ALCANCE[recibo.alcance] ?? recibo.alcance}</dd>
        </div>
      {/if}
      {#if recibo.version}
        <div class="campo">
          <dt>Versión</dt>
          <dd class="monoespaciado">{recibo.version}</dd>
        </div>
      {/if}
      {#if recibo.momento}
        <div class="campo">
          <dt>Fecha</dt>
          <dd><time use:ayudaContextual datetime={recibo.momento} title={recibo.momento}>{comoFecha(recibo.momento)}</time></dd>
        </div>
      {/if}
      {#if recibo.secuencia !== undefined && recibo.secuencia !== null}
        <div class="campo">
          <dt>N.º de registro</dt>
          <dd class="monoespaciado">{recibo.secuencia}</dd>
        </div>
      {/if}
      {#if recibo.huella}
        <div class="campo ancho">
          <dt>Comprobante</dt>
          <dd class="monoespaciado huella">{recibo.huella}</dd>
        </div>
      {/if}
    </dl>

    <p class="nota">
      Este comprobante lo calculó y lo guardó el servidor. Puedes anotarlo para
      referirte a esta decisión más adelante.
    </p>
  </section>
{/if}

<style>
  .recibo {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 14px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo);
    border-inline-start: 3px solid var(--accent-main);
    border-radius: var(--radius-sm);
  }

  .cabecera { display: flex; align-items: center; gap: 8px; }

  .sello {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 24px;
    block-size: 24px;
    background: var(--accent-surface);
    color: var(--accent-main);
    border-radius: 50%;
    flex-shrink: 0;
  }

  h3 {
    margin: 0;
    font-size: var(--texto-base);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .campos {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px 12px;
    margin: 0;
  }

  .campo.ancho { grid-column: 1 / -1; }

  dt {
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  dd {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
    line-height: 1.4;
  }

  .monoespaciado { font-family: var(--fuente-mono, ui-monospace, monospace); }

  .huella {
    font-size: var(--texto-xs);
    overflow-wrap: anywhere;
    user-select: all;
  }

  .nota {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.4;
  }

  @media (max-width: 30rem) {
    .campos { grid-template-columns: 1fr; }
  }
</style>
