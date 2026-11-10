
<script>
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import { toast } from '../../../comun/estado/toasts.svelte.js';
  import {
    motivoParaNoSubir,
    TAMANO_MAXIMO_BYTES
  } from '../../../nucleo/api/consentimiento.js';

  let {
    alSubir,
    errorDelServidor = '',
    reservaPendiente = false
  } = $props();

  let archivo = $state(null);
  let entradaArchivo = $state(null);
  let enviando = $state(false);
  let confirmando = $state(false);
  let motivoLocal = $state('');

  const megas = (TAMANO_MAXIMO_BYTES / 1024 / 1024).toFixed(0);

  function comoTamano(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function alElegir(evento) {
    const elegido = evento.currentTarget?.files?.[0] ?? null;
    motivoLocal = elegido ? motivoParaNoSubir(elegido) : '';
    archivo = motivoLocal ? null : elegido;
  }

  function pedirConfirmacion() {
    if (!archivo || enviando) return;
    confirmando = true;
  }

  async function confirmar() {
    if (enviando || !archivo) return;
    enviando = true;
    try {
      await alSubir(archivo);
      toast.exito('Autorización recibida para revisión.');
      confirmando = false;
      archivo = null;
      if (entradaArchivo) entradaArchivo.value = '';
    } catch {
      confirmando = false;
    } finally {
      enviando = false;
    }
  }
</script>

<div class="carga">
  <p class="requisitos">
    PDF de hasta <strong>{megas} MB</strong>. Se guarda de forma privada.
  </p>

  <label class="selector" for="archivo-evidencia">
    <Icono nombre="descarga" medida={16} />
    <span>{archivo ? archivo.name : 'Elegir el archivo PDF'}</span>
  </label>
  <input
    id="archivo-evidencia"
    class="entrada-archivo solo-lectura-asistida"
    type="file"
    accept="application/pdf,.pdf"
    bind:this={entradaArchivo}
    onchange={alElegir}
    disabled={enviando}
  />

  {#if archivo}
    <p class="elegido">
      <Icono nombre="check" medida={13} />
      <span>{archivo.name} · {comoTamano(archivo.size)}</span>
    </p>
  {/if}

  {#if motivoLocal}
    <p class="aviso" role="alert">{motivoLocal}</p>
  {/if}

  {#if reservaPendiente}

    <p class="aviso" role="alert">
      Tu archivo llegó, pero el sistema no pudo terminar de guardarlo. La carga
      quedó registrada como pendiente y el equipo puede completarla. No hace
      falta que vuelvas a subirlo ahora mismo; si lo prefieres, inténtalo más
      tarde.
    </p>
  {:else if errorDelServidor}
    <p class="aviso" role="alert">{errorDelServidor}</p>
  {/if}

  <div class="acciones">
    <Boton onclick={pedirConfirmacion} deshabilitado={!archivo || enviando}>
      <Icono nombre="enviar" medida={15} />
      {enviando ? 'Enviando…' : 'Enviar la autorización'}
    </Boton>
  </div>
</div>

<Dialogo bind:abierto={confirmando} tipo="confirmar" titulo="¿Enviar esta autorización?">
  <p>
    Se enviará <strong>{archivo?.name ?? ''}</strong> al almacenamiento privado
    del proyecto y quedará registrado como un intento con su fecha y su huella.
  </p>
  <p>
    Enviarla <strong>no habilita el tutor todavía</strong>: una persona
    autorizada tiene que revisarla y aprobarla. Verás el estado en esta misma
    pantalla.
  </p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmando = false)} deshabilitado={enviando}>
      Volver
    </Boton>
    <Boton onclick={confirmar} deshabilitado={enviando}>
      {enviando ? 'Enviando…' : 'Sí, enviar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .carga { position: relative; display: flex; flex-direction: column; gap: 8px; min-inline-size: 0; }

  .requisitos {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .entrada-archivo {
    inset: 0 auto auto 0;
  }

  .selector {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 14px;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
    background: var(--surface-paper);
    border: 1.5px dashed var(--trazo);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition-fast);
    min-inline-size: 0;
    max-inline-size: 100%;
    overflow-wrap: anywhere;
    text-align: center;
  }

  .selector:hover { border-color: var(--accent-main); background: var(--surface-canvas); }

  .selector:has(+ .entrada-archivo:focus-visible),
  .selector:focus-within { outline: 2px solid var(--accent-main); outline-offset: 2px; }

  .elegido {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    overflow-wrap: anywhere;
  }

  .aviso {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--semantic-error);
    background: var(--surface-paper);
    border: 1px solid var(--semantic-error);
    border-radius: var(--radius-xs);
  }

  .aviso::before { content: '⚠ '; }

  .acciones { display: flex; justify-content: flex-end; }

  @media (max-width: 30rem) {
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
