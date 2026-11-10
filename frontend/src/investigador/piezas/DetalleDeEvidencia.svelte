<!--
Una evidencia abierta: metadatos, documento y decisión · C2B.

LA REGLA CENTRAL DE ESTA PANTALLA, ANTES QUE NADA
---------------------------------------------------
**Aprobar y rechazar están deshabilitados hasta que el PDF se haya recuperado
correctamente.** No es una cortesía de interfaz: es lo que impide que alguien
resuelva una autorización que nunca vio.

Y se dice **por qué** están deshabilitados. Un botón gris sin explicación se lee
como un fallo de la aplicación, y quien lo encuentra recarga, prueba con otro
navegador y acaba pensando que el sistema está roto — cuando lo que pasa es que
el documento no se pudo recuperar y eso es exactamente lo que hay que saber.

⚠️ **Esto NO es un comprobante de lectura.** Que los bytes llegaran no demuestra
que una persona los mirara, y el sistema no finge lo contrario: no se registra
ningún «leído», no se cronometra nada y no se envía ninguna señal al servidor
cuando el visor termina de pintar. Lo único que se afirma es lo que se puede
afirmar — que el documento estaba disponible cuando se tomó la decisión—.

TRES ESTADOS DEL DOCUMENTO, Y NINGUNO SE CONFUNDE
---------------------------------------------------
· **cargando** — se está pidiendo; no se decide todavía;
· **disponible** — hay `Blob`; se puede ver y se puede decidir;
· **no recuperable** — 503, reserva sin confirmar, archivo ausente. Se explica
  con el motivo que redactó el servidor y **no se habilita nada**.

Una reserva sin confirmar cae en el tercero, y es el caso que la corrección de
C2A creó a propósito: el backend responde 503 con un motivo de reconciliación en
vez de servir un documento que todavía no es evidencia.



-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import VisorDePdf from './VisorDePdf.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import { fechaLegible } from '../../nucleo/formato/fechas.js';

  let {
    /** El documento de `GET /api/representante/evidencias/{id}`, o `null`. */
    detalle = null,
    /** El `Blob` del PDF, o `null` si todavía no llegó o no se pudo. */
    documento = null,
    /** Petición del detalle en vuelo. */
    cargandoDetalle = false,
    /** Petición del archivo en vuelo. */
    cargandoArchivo = false,
    /** `describir(error)` del detalle, o `null`. */
    falloDetalle = null,
    /** `describir(error)` del archivo, o `null`. Distinto del anterior: el
        detalle puede haber llegado y el archivo no. */
    falloArchivo = null,
    /** Si hay una decisión en vuelo. Bloquea los dos botones. */
    resolviendo = false,
    /** El recibo de la última decisión tomada aquí, o `null`. */
    recibo = null,
    /** Sólo en móvil: vuelve a la lista. `null` en escritorio. */
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

  /** La única condición que abre los botones. Ver la cabecera. */
  const puedeDecidir = $derived(
    Boolean(documento) && !cargandoArchivo && !resolviendo && detalle?.estado === 'pendiente'
  );

  /** Por qué no se puede decidir. Vacío cuando sí se puede. */
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
      <!-- El SHA-256 es lo que permite comprobar que el archivo que se está
           viendo es el que se registró. Se enseña recortado y entero en el
           `title`: los 64 caracteres completos no caben y nadie los lee. -->
      <div>
        <dt>Huella</dt>
        <dd><code use:ayudaContextual title={detalle.sha256}>{String(detalle.sha256).slice(0, 16)}…</code></dd>
      </div>
      {#if detalle.revisada_en}
        <div><dt>Revisada</dt><dd>{fechaLegible(detalle.revisada_en)}</dd></div>
      {/if}
    </dl>

    <!-- El motivo histórico de un rechazo · decisión ratificada 5. Sin esto,
         una decisión de hace dos semanas deja de ser comprensible; el listado
         no lo trae y esta pantalla es la única que puede enseñarlo. -->
    {#if detalle.estado === 'rechazada' && detalle.motivo}
      <div class="motivo-historico">
        <h3>Motivo del rechazo</h3>
        <p>{detalle.motivo}</p>
      </div>
    {/if}

    <!-- ── el documento ────────────────────────────────────────────────── -->
    {#if cargandoArchivo}
      <CargadorCubo mensaje="Recuperando el documento…" pantallaCompleta />
    {:else if falloArchivo}
      <Degradacion
        respuesta={falloArchivo}
        alReintentar={falloArchivo.reintentable ? alReintentarArchivo : null} />
    {:else if documento}
      <VisorDePdf {documento} evidencia={detalle.evidencia} />
    {/if}

    <!-- ── el recibo de lo que se acaba de decidir ─────────────────────── -->
    {#if recibo}
      <div class="recibo" role="status">
        <Icono nombre="check" medida={15} />
        <span>
          Registrada como <strong>{ESTADOS[recibo.resultado] ?? recibo.resultado}</strong>
          el {fechaLegible(recibo.revisada_en)}.
        </span>
      </div>
    {/if}

    <!-- ── la decisión ─────────────────────────────────────────────────── -->
    {#if detalle.estado === 'pendiente'}
      <div class="decision">
        {#if motivoBloqueo}
          <!-- Se explica SIEMPRE que los botones estén cerrados. Un botón gris
               sin motivo se lee como una aplicación rota. -->
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

  /*
    En escritorio no hay nada a lo que volver: las dos columnas están a la vez.
    Se oculta con la MISMA consulta de medios que reparte las columnas en
    `Evidencias.svelte`, y no condicionando la prop desde el guion: el punto de
    corte tiene que vivir en un solo idioma, o la copia que se olvide de
    actualizarse deja un botón que no lleva a ninguna parte.
  */
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
    /* Una huella de 64 caracteres no puede ensanchar la columna. */
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
