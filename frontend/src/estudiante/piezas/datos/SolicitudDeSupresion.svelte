
<script>
  import CargadorCubo from '../../../comun/base/CargadorCubo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Campo from '../../../comun/base/Campo.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import ReautenticarConGoogle from '../../../comun/sesion/ReautenticarConGoogle.svelte';
  import * as gobierno from '../../../nucleo/api/gobierno.js';
  import { describir, clasificar } from '../../../nucleo/errores/degradacion.js';

  let {
    alCambiar
  } = $props();

  const FRASE_VISIBLE = 'ELIMINAR MIS DATOS';

  let tramite = $state(null);
  let cargando = $state(true);
  let fallo = $state('');

  let reautenticada = $state(false);
  let frase = $state('');
  let enviando = $state(false);
  let confirmandoSolicitud = $state(false);
  let confirmandoCancelacion = $state(false);
  let motivoDelServidor = $state('');
  let avisoEnviado = $state(null);

  const abierta = $derived(tramite?.abierta ?? null);

  function comoFecha(iso) {
    if (!iso) return '';
    const fecha = new Date(iso);
    if (Number.isNaN(fecha.getTime())) return iso;
    return fecha.toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
  }

  function motivoDe(error) {
    const clase = clasificar(error);
    if (clase === 'sin-sesion' && error?.estadoDelServidor === 'reautenticacion_requerida') {
      reautenticada = false;
      return 'Tu comprobación con Google caducó. Vuelve a hacerla y repite la solicitud.';
    }
    return error?.detalle || describir(error).titulo;
  }

  async function cargar() {
    cargando = true;
    fallo = '';
    try {
      tramite = await gobierno.consultar();
    } catch (e) {
      tramite = null;
      fallo = motivoDe(e);
    } finally {
      cargando = false;
    }
  }

  async function solicitar() {
    if (enviando) return;
    enviando = true;
    motivoDelServidor = '';
    try {
      const respuesta = await gobierno.solicitar(frase);
      avisoEnviado = respuesta?.aviso_enviado ?? null;
      confirmandoSolicitud = false;
      frase = '';
      await cargar();
      alCambiar?.();
    } catch (e) {
      motivoDelServidor = motivoDe(e);
      confirmandoSolicitud = false;
    } finally {
      enviando = false;
    }
  }

  async function cancelar() {
    if (enviando) return;
    enviando = true;
    motivoDelServidor = '';
    try {
      await gobierno.cancelar();
      confirmandoCancelacion = false;
      await cargar();
      alCambiar?.();
    } catch (e) {
      motivoDelServidor = motivoDe(e);
      confirmandoCancelacion = false;
    } finally {
      enviando = false;
    }
  }

  $effect(() => { cargar(); });
</script>

<section class="supresion" aria-labelledby="titulo-supresion">
  <div class="cabecera">
    <Icono nombre="basura" medida={16} />
    <h2 id="titulo-supresion">Eliminar mis datos</h2>
  </div>

  {#if cargando}
    <CargadorCubo mensaje="Consultando si tienes un trámite abierto…" compacto />

  {:else if fallo}
    <p class="aviso" role="alert">{fallo}</p>
    <Boton variante="secundario" onclick={cargar}>Volver a intentarlo</Boton>

  {:else if abierta}

    <div class="en-curso" role="status">
      <p class="en-curso-titulo">
        Tienes una solicitud de eliminación <strong>en curso</strong>.
        Tus datos todavía no se han eliminado.
      </p>

      <dl class="plazos">
        <div>
          <dt>La pediste</dt>
          <dd><time datetime={abierta.solicitada_en}>{comoFecha(abierta.solicitada_en)}</time></dd>
        </div>
        <div>
          <dt>Puedes cancelarla hasta</dt>
          <dd>
            <time datetime={abierta.cancelable_hasta}>{comoFecha(abierta.cancelable_hasta)}</time>
            <span class="nota-plazo">(24 horas desde que la pediste)</span>
          </dd>
        </div>
        <div>
          <dt>Se resolverá antes de</dt>
          <dd><time datetime={abierta.resolver_antes_de}>{comoFecha(abierta.resolver_antes_de)}</time></dd>
        </div>
        {#if abierta.extension_hasta}
          <div>
            <dt>Ampliada hasta</dt>
            <dd>
              <time datetime={abierta.extension_hasta}>{comoFecha(abierta.extension_hasta)}</time>
              {#if abierta.extension_motivo}<span class="nota-plazo">{abierta.extension_motivo}</span>{/if}
            </dd>
          </div>
        {/if}
      </dl>

      {#if avisoEnviado === false}
        <p class="nota-correo">
          El aviso por correo no pudo enviarse. El trámite sigue abierto de todas
          formas: el correo informa, no decide.
        </p>
      {/if}

      {#if motivoDelServidor}
        <p class="aviso" role="alert">{motivoDelServidor}</p>
      {/if}

      <Boton variante="secundario" onclick={() => (confirmandoCancelacion = true)} deshabilitado={enviando}>
        <Icono nombre="volver" medida={15} />
        Cancelar la solicitud
      </Boton>
    </div>

  {:else}
    <p class="explica">
      Puedes pedir que se elimine tu información. <strong>No se borra nada al
      pulsar</strong>: se abre una solicitud, tienes 24 horas para cancelarla y
      el equipo la resuelve en el plazo que marca la ley.
    </p>

    <ol class="pasos">
      <li class:hecho={reautenticada}>
        <span class="numero">1</span>
        <div>
          <p class="paso-titulo">Comprueba tu identidad con Google</p>
          {#if reautenticada}
            <p class="paso-nota">Comprobado. Puedes continuar.</p>
          {:else}
            <p class="paso-nota">
              Hace falta un acceso reciente, no el de hace un rato.
            </p>
            <ReautenticarConGoogle alAcreditar={() => (reautenticada = true)} />
          {/if}
        </div>
      </li>

      <li class:inactivo={!reautenticada}>
        <span class="numero">2</span>
        <div>
          <p class="paso-titulo">Escribe la frase de confirmación</p>
          <p class="paso-nota">
            Escribe exactamente: <strong class="frase">{FRASE_VISIBLE}</strong>
          </p>
          <Campo
            etiqueta="Frase de confirmación"
            bind:valor={frase}
            disabled={!reautenticada || enviando}
            ayuda="La comprueba el sistema, no esta pantalla."
          />
        </div>
      </li>
    </ol>

    {#if motivoDelServidor}
      <p class="aviso" role="alert">{motivoDelServidor}</p>
    {/if}

    <div class="accion-supresion">
    <Boton
      onclick={() => (confirmandoSolicitud = true)}
      deshabilitado={!reautenticada || !frase.trim() || enviando}
    >
      <Icono nombre="basura" medida={15} />
      Solicitar la eliminación
    </Boton>
    </div>
  {/if}

  {#if tramite?.historial?.length}
    <details class="historial">
      <summary>Solicitudes anteriores ({tramite.historial.length})</summary>
      <ul>
        {#each tramite.historial as h (h.solicitada_en)}
          <li>
            <strong>{h.estado}</strong> ·
            <time datetime={h.solicitada_en}>{comoFecha(h.solicitada_en)}</time>
            {#if h.cerrada_en}
              — cerrada el <time datetime={h.cerrada_en}>{comoFecha(h.cerrada_en)}</time>
            {/if}
          </li>
        {/each}
      </ul>
    </details>
  {/if}
</section>

<Dialogo bind:abierto={confirmandoSolicitud} tipo="eliminar" titulo="¿Solicitar la eliminación de tus datos?">
  <p>
    Se abrirá una solicitud y <strong>el tutor quedará bloqueado</strong>
    mientras esté en curso. No se registrará ningún dato nuevo.
  </p>
  <p>
    <strong>Tus datos no se eliminan ahora.</strong> Tendrás 24 horas para
    cancelarla desde esta misma pantalla.
  </p>

  <p>
    El sistema intentará enviarte un aviso a tu correo institucional. Si el
    envío falla, la solicitud sigue siendo válida y esta pantalla te mostrará su
    estado.
  </p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmandoSolicitud = false)} deshabilitado={enviando}>
      Volver
    </Boton>
    <Boton onclick={solicitar} deshabilitado={enviando}>
      {enviando ? 'Enviando…' : 'Sí, solicitar'}
    </Boton>
  {/snippet}
</Dialogo>

<Dialogo bind:abierto={confirmandoCancelacion} tipo="confirmar" titulo="¿Cancelar la solicitud?">
  <p>
    La solicitud se cerrará y tus datos se conservarán. Volverás a poder usar el
    tutor si el resto de tus autorizaciones siguen en orden.
  </p>
  <p>Podrás volver a solicitar la eliminación cuando quieras.</p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmandoCancelacion = false)} deshabilitado={enviando}>
      Dejarla como está
    </Boton>
    <Boton onclick={cancelar} deshabilitado={enviando}>
      {enviando ? 'Cancelando…' : 'Sí, cancelar la solicitud'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .supresion {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 14px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .cabecera { display: flex; align-items: center; gap: 8px; color: var(--ink-secondary); }

  h2 {
    margin: 0;
    font-size: var(--texto-base);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .explica {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .pasos {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .pasos li { display: flex; gap: 10px; align-items: flex-start; }

  .pasos li.inactivo { opacity: 0.6; }

  .numero {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 22px;
    block-size: 22px;
    flex-shrink: 0;
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--accent-main);
    background: var(--accent-surface);
    border-radius: 50%;
  }

  .pasos li.hecho .numero { color: var(--surface-paper); background: var(--accent-main); }

  .paso-titulo {
    margin: 0 0 2px;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  .paso-nota {
    margin: 0 0 6px;
    font-size: var(--texto-xs);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .frase {
    font-family: var(--fuente-mono, ui-monospace, monospace);
    letter-spacing: 0.03em;
    user-select: all;
  }

  .en-curso {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px 12px;
    background: var(--surface-canvas);
    border-inline-start: 3px solid var(--accent-main);
    border-radius: var(--radius-xs);
  }

  .en-curso-titulo {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-primary);
  }

  .plazos { margin: 0; display: flex; flex-direction: column; gap: 6px; }

  .plazos dt {
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .plazos dd {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .nota-plazo { color: var(--ink-secondary); font-size: var(--texto-xs); }

  .nota-correo {
    margin: 0;
    font-size: var(--texto-xs);
    line-height: 1.45;
    color: var(--ink-secondary);
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

  .historial { font-size: var(--texto-sm); color: var(--ink-secondary); }

  .historial summary { cursor: pointer; }

  .historial ul { margin: 6px 0 0; padding-inline-start: 1.2em; }

  .accion-supresion { position: relative; align-self: flex-start; max-inline-size: 100%; isolation: isolate; }
  .accion-supresion :global(button) { position: relative; z-index: 1; min-block-size: 44px; background: var(--cuenta-peligro-solido); color: var(--cuenta-peligro-tinta); border-color: transparent; }
  .accion-supresion :global(button:hover:not(:disabled)) { background: var(--cuenta-peligro-solido); }
  .accion-supresion::before { content: ''; position: absolute; inset: 0; border: 2px solid var(--cuenta-peligro-particula); border-radius: var(--radius-trazado); pointer-events: none; animation: radiacionSupresion 2.8s ease-out infinite; }
  .accion-supresion::after { content: ''; position: absolute; inset-inline-start: 50%; inset-block-start: 50%; inline-size: 3px; block-size: 3px; border-radius: 50%; background: var(--cuenta-peligro-particula); box-shadow: -100px -26px var(--cuenta-peligro-particula), 95px 25px var(--cuenta-peligro-particula), -70px 27px var(--cuenta-peligro-particula), 72px -25px var(--cuenta-peligro-particula); pointer-events: none; animation: particulasSupresion 2.8s ease-in-out infinite; }
  :global(body.dark-theme) .accion-supresion :global(button) { border-color: var(--cuenta-peligro); }
  @keyframes radiacionSupresion { 0% { transform: scale(1); opacity: .7; } 100% { transform: scale(1.08, 1.4); opacity: 0; } }
  @keyframes particulasSupresion { 0%,100% { transform: scale(.9); opacity: .25; } 50% { transform: scale(1.1); opacity: .7; } }
  @media (prefers-reduced-motion: reduce) { .accion-supresion::before, .accion-supresion::after { animation: none; opacity: .35; } }
</style>
