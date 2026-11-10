
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import VisorDePdf from './VisorDePdf.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import { fechaLegible } from '../../nucleo/formato/fechas.js';

  let {
    detalle = null,
    documento = null,
    cargandoDetalle = false,
    cargandoArchivo = false,
    falloDetalle = null,
    falloArchivo = null,
    resolviendo = false,
    recibo = null,
    alVolver = null,
    alReintentarArchivo,
    alAprobar,
    alRechazar
  } = $props();

  const ESTADOS = {
    pendiente: 'Sin revisar',
    aprobada: 'Aprobada',
    rechazada: 'Rechazada'
  };

  const puedeDecidir = $derived(
    Boolean(documento) && !cargandoArchivo && !resolviendo && detalle?.estado === 'pendiente'
  );

  const motivoBloqueo = $derived(
    !detalle
      ? ''
      : detalle.estado !== 'pendiente'
        ? 'Este intento ya se resolvió. Para corregir, el estudiante tiene que cargar un documento nuevo.'
        : cargandoArchivo
          ? 'Se está recuperando el documento.'
          : !documento
            ? 'No se puede decidir sin haber podido abrir el documento.'
            : ''
  );

  const kilobytes = $derived(Math.max(1, Math.round((detalle?.tamano_bytes ?? 0) / 1024)));
  const clases = $derived(
    Array.isArray(detalle?.estudiante?.clases) ? detalle.estudiante.clases.filter(Boolean) : []
  );
</script>

<section class="detalle" aria-label="Autorización seleccionada">
  {#if alVolver}
    <button type="button" class="volver" onclick={alVolver}>
      <Icono nombre="volver" medida={15} />
      <span>Volver a la lista</span>
    </button>
  {/if}

  {#if cargandoDetalle && !detalle}
    <CargadorCubo mensaje="Cargando la autorización…" compacto />
  {/if}

  {#if falloDetalle}
    <Degradacion respuesta={falloDetalle} />
  {/if}

  {#if detalle}
    <header class="cabeza">
      <h2>Intento {detalle.intento}</h2>
      <span class="estado {detalle.estado}">{ESTADOS[detalle.estado] ?? detalle.estado}</span>
    </header>

    <dl class="metadatos">
      <div><dt>Estudiante</dt><dd>{detalle.estudiante?.nombre || 'Nombre no disponible'}</dd></div>
      <div>
        <dt>{clases.length === 1 ? 'Clase' : 'Clases'}</dt>
        <dd>{clases.length ? clases.join(' · ') : 'Sin clase vinculada'}</dd>
      </div>
      <div><dt>Recibida</dt><dd>{fechaLegible(detalle.recibido_en)}</dd></div>
      <div><dt>Documento</dt><dd>{detalle.tipo_mime} · {kilobytes} KB</dd></div>
      <div><dt>Versión firmada</dt><dd><code>{detalle.version}</code></dd></div>

      <div>
        <dt>Huella</dt>
        <dd><code use:ayudaContextual title={detalle.sha256}>{String(detalle.sha256).slice(0, 16)}…</code></dd>
      </div>
      {#if detalle.revisada_en}
        <div><dt>Revisada</dt><dd>{fechaLegible(detalle.revisada_en)}</dd></div>
      {/if}
    </dl>


    {#if detalle.estado === 'rechazada' && detalle.motivo}
      <div class="motivo-historico">
        <h3>Motivo del rechazo</h3>
        <p>{detalle.motivo}</p>
      </div>
    {/if}


    {#if cargandoArchivo}
      <CargadorCubo mensaje="Recuperando el documento…" pantallaCompleta />
    {:else if falloArchivo}
      <Degradacion
        respuesta={falloArchivo}
        alReintentar={falloArchivo.reintentable ? alReintentarArchivo : null} />
    {:else if documento}
      <VisorDePdf {documento} evidencia={detalle.evidencia} />
    {/if}


    {#if recibo}
      <div class="recibo" role="status">
        <Icono nombre="check" medida={15} />
        <span>
          Registrada como <strong>{ESTADOS[recibo.resultado] ?? recibo.resultado}</strong>
          el {fechaLegible(recibo.revisada_en)}.
        </span>
      </div>
    {/if}


    {#if detalle.estado === 'pendiente'}
      <div class="decision">
        {#if motivoBloqueo}

          <p class="por-que" id="por-que-bloqueado">{motivoBloqueo}</p>
        {/if}
        <div class="botones" aria-describedby={motivoBloqueo ? 'por-que-bloqueado' : undefined}>
          <Boton variante="secundario" deshabilitado={!puedeDecidir} onclick={alRechazar}>
            Rechazar
          </Boton>
          <Boton deshabilitado={!puedeDecidir} onclick={alAprobar}>
            Aprobar
          </Boton>
        </div>
      </div>
    {:else}
      <p class="por-que">{motivoBloqueo}</p>
    {/if}
  {/if}
</section>

<style>
  .detalle {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    min-inline-size: 0;
  }

  .volver {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    align-self: flex-start;
    padding: 4px 10px 4px 6px;
    background: transparent;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
  }

  .volver:hover { border-color: var(--accent-main); color: var(--accent-main); }

  @media (min-width: 60.0625rem) {
    .volver { display: none; }
  }

  .cabeza {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
    flex-wrap: wrap;
  }

  h2 { margin: 0; font-size: var(--texto-lg); font-weight: 700; color: var(--ink-primary); }

  .estado {
    padding: 3px 10px;
    border-radius: var(--radius-pill, 9999px);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--trazo-suave);
    color: var(--ink-secondary);
    background: var(--surface-paper);
  }

  .estado.aprobada {
    color: var(--semantic-success);
    background: var(--semantic-success-bg);
    border-color: var(--semantic-success);
  }

  .estado.rechazada {
    color: var(--semantic-danger, var(--ink-secondary));
    background: var(--semantic-danger-bg, var(--surface-paper));
    border-color: var(--semantic-danger, var(--trazo-suave));
  }

  .metadatos {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: var(--espacio-sm) var(--espacio-md);
    margin: 0;
  }

  .metadatos dt {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .metadatos dd {
    margin: 2px 0 0;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
    overflow-wrap: anywhere;
  }

  code { font-family: var(--fuente-mono, monospace); font-size: var(--texto-xs); }

  .motivo-historico {
    padding: var(--espacio-sm) var(--espacio-md);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    background: var(--surface-panel);
  }

  .motivo-historico h3 {
    margin: 0 0 4px;
    font-size: var(--texto-xs);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .motivo-historico p {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .cargando { margin: 0; font-size: var(--texto-sm); color: var(--ink-tertiary); }

  .recibo {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: var(--espacio-sm) var(--espacio-md);
    border: 1px solid var(--semantic-success);
    border-radius: var(--radius-md);
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
    font-size: var(--texto-sm);
  }

  .decision {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-block-start: var(--espacio-sm);
    border-block-start: 1px solid var(--trazo-suave);
  }

  .por-que {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
  }

  .botones { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
