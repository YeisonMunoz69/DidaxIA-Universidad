<!--
El recibo que devolvió el servidor · `EQ-021`, hito R3.

⚠️ ESTE COMPONENTE NO CALCULA NADA, Y ES SU RAZÓN DE SER
---------------------------------------------------------
Los seis campos —secuencia, momento, versión, alcance, decisión y huella— los
asigna PostgreSQL y los devuelve `_recibo()`. La huella es el SHA-256 que
`comprobante_de()` calcula en el servidor sobre sujeto, código de versión,
huella del documento y decisión.

Un comprobante que el navegador construyera probaría lo que el navegador
quisiera. Por eso aquí sólo se pinta lo que llegó: si un campo falta, se dice
que falta; no se rellena con la hora del equipo ni con un identificador local.

Sin `secuencia` y `momento`, dos actos idénticos del mismo sujeto sobre la
misma versión serían indistinguibles en el recibo — por eso los seis se
enseñan y no sólo la huella.

Y no se guarda en ningún almacén del navegador: es la constancia de un acto
sobre datos personales y vive donde vive el acto.



-->
<script>
  import { ayudaContextual } from '../../../comun/base/ayudaContextual.js';
  import Icono from '../../../comun/base/Icono.svelte';

  let {
    /** El objeto `recibo` de la respuesta. Tal cual llegó. */
    recibo,
    /** Qué se acaba de hacer, para encabezarlo en lenguaje humano. */
    titulo = 'Quedó registrado'
  } = $props();

  /** Cómo se nombra cada decisión. El valor crudo también se enseña. */
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

  /**
   * La fecha, en la zona del navegador y con su valor original a la vista.
   *
   * El servidor manda ISO 8601 con zona; formatearlo es presentación. Se
   * conserva el original en `title` para que quien tenga que auditarlo pueda
   * leer exactamente lo que se guardó, sin depender del reloj de nadie.
   */
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

  /* La huella son 64 caracteres: se parte donde quepa en vez de desbordar la
     tarjeta a 360 px, y se puede seleccionar entera para copiarla. */
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
