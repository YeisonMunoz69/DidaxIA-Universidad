
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import Icono from '../../comun/base/Icono.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import EntradaInstitucional from '../piezas/recorrido/EntradaInstitucional.svelte';
  import PanelDeEstado from '../piezas/recorrido/PanelDeEstado.svelte';
  import FormularioDePerfil from '../piezas/recorrido/FormularioDePerfil.svelte';
  import DecisionConjunta from '../piezas/recorrido/DecisionConjunta.svelte';
  import DocumentoDeLaVersion from '../piezas/recorrido/DocumentoDeLaVersion.svelte';
  import PanelDelRepresentante from '../piezas/recorrido/PanelDelRepresentante.svelte';
  import ReciboDelActo from '../piezas/recorrido/ReciboDelActo.svelte';
  import EnlacesPublicos from '../../comun/base/EnlacesPublicos.svelte';
  import EntrarConGoogle from '../../comun/sesion/EntrarConGoogle.svelte';
  import ReportarProblema from '../../comun/rutas/ReportarProblema.svelte';
  import * as onboarding from '../../nucleo/api/onboarding.js';
  import * as consentimiento from '../../nucleo/api/consentimiento.js';
  import * as sesionApi from '../../nucleo/api/sesion.js';
  import { describir, clasificar } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { esBloqueo } from '../../nucleo/sesion/acceso.js';

  const codigoDocumento = new URLSearchParams(globalThis.location?.search ?? '').get('documento') ?? '';

  let estado = $state(null);
  let versiones = $state(null);
  let versionesNoDisponibles = $state(false);
  let identidad = $state(null);
  let recibos = $state([]);
  let avisoEnviado = $state(null);

  let cargando = $state(true);
  let fallo = $state(null);
  let errorDelPerfil = $state('');
  let errorDeDecision = $state('');
  let sinVersionAlDecidir = $state(false);
  let motivoDeLaPolitica = $state('');
  let alcancesFaltantes = $state([]);
  let errorDeEvidencia = $state('');
  let reservaPendiente = $state(false);
  let refrescandoRepresentante = $state(false);
  let dialogoDeRechazoAbierto = $state(false);
  let rechazoAnunciado = $state(false);
  let motivoDelRechazo = $state('');

  const acceso = $derived(estado?.acceso ?? sesion.acceso);

  const enBloqueo = $derived(
    acceso === 'mantenimiento' || acceso === 'eliminacion_solicitada' || esBloqueo(acceso)
  );

  const bloqueoConSalida = $derived(
    esBloqueo(acceso) && estado?.decision?.requerida === true
  );

  const titulo = $derived(
    codigoDocumento
      ? 'Documento vigente de consentimiento'
      : !sesion.autenticada && sesion.sincronizada
      ? 'Entra con tu cuenta de la universidad'
      : representanteEsPasoActual
      ? ({
          pendiente_documento: 'Autorización de tu representante',
          documento_recibido: 'Autorización en revisión',
          rechazado: 'Corrige la autorización de tu representante',
          aprobado: 'Autorización aprobada'
        }[estado?.representante?.estado] ?? 'Autorización de tu representante')
      : {
          mantenimiento: 'El servicio está en mantenimiento',
          eliminacion_solicitada: 'Tu solicitud de eliminación está en curso',
          bloqueado_por_rechazo: 'El tutor está bloqueado',
          bloqueado_por_revocacion: 'El tutor está bloqueado',
          esperando_representante: 'Falta la autorización de tu representante'
        }[acceso] ?? 'Antes de empezar tu tutoría'
  );

  const faltaPerfil = $derived(estado?.perfil?.completo === false);

  const faltaDecision = $derived(
    Boolean(estado) &&
      !faltaPerfil &&
      (estado.decision?.requerida === true ||
        estado.consentimiento?.al_dia !== true ||
        (esMenor && estado.asentimiento?.al_dia !== true))
  );

  const puedeAceptar = $derived(estado?.decision?.puede_aceptar ?? true);
  const puedeRechazar = $derived(estado?.decision?.puede_rechazar ?? true);

  const esMenor = $derived(
    typeof estado?.perfil?.edad === 'number' && estado.perfil.edad < 18
  );

  const representanteEsPasoActual = $derived(
    Boolean(estado) &&
      esMenor &&
      !faltaPerfil &&
      estado.consentimiento?.al_dia === true &&
      estado.asentimiento?.al_dia === true &&
      ['pendiente_documento', 'documento_recibido', 'rechazado', 'aprobado', 'vencido'].includes(
        estado.representante?.estado
      )
  );

  function aplicarRespuesta(respuesta) {
    estado = respuesta;
    sesion.aplicarAcceso(
      respuesta.acceso,
      respuesta.tutoria_academica_sin_investigacion
    );
    if (Array.isArray(respuesta.recibos) && respuesta.recibos.length) {
      recibos = respuesta.recibos;
    } else if (respuesta.recibo) {
      recibos = [respuesta.recibo];
    }
    if (respuesta.acceso !== 'habilitado') return;
    navegar('/');
  }

  function motivoDe(error) {
    const clase = clasificar(error);
    if (clase === 'mantenimiento') {
      sesion.aplicarAcceso('mantenimiento');
      estado = null;
      return '';
    }
    if (clase === 'sin-sesion') {
      sesion.sincronizar();
      return '';
    }
    return error?.detalle || describir(error).titulo;
  }

  async function cargar() {
    if (!sesion.autenticada) {
      cargando = false;
      estado = null;
      return;
    }
    cargando = true;
    fallo = null;
    try {
      if (codigoDocumento) {
        estado = null;
        return;
      }
      estado = await onboarding.estado();
      sesion.aplicarAcceso(
        estado.acceso,
        estado.tutoria_academica_sin_investigacion
      );
      if (estado.acceso === 'habilitado') {
        navegar('/');
        return;
      }
      if (!enBloqueo || estado.decision?.requerida === true || representanteEsPasoActual) {
        const [v, s] = await Promise.allSettled([
          consentimiento.versiones(),
          sesionApi.consultar()
        ]);
        if (v.status === 'fulfilled') {
          versiones = v.value;
          versionesNoDisponibles = false;
        } else {
          versiones = null;
          versionesNoDisponibles = true;
        }
        if (s.status === 'fulfilled') {
          identidad = { nombre: s.value?.nombre ?? '', correo: s.value?.correo ?? '' };
        }
      }
    } catch (e) {
      const clase = clasificar(e);
      if (clase === 'sin-sesion') {
        await sesion.sincronizar();
        estado = null;
      } else if (clase === 'mantenimiento') {
        estado = null;
        sesion.aplicarAcceso('mantenimiento');
      } else {
        fallo = describir(e);
      }
    } finally {
      cargando = false;
    }
  }

  async function guardarPerfil(valores) {
    errorDelPerfil = '';
    try {
      aplicarRespuesta(await onboarding.guardarPerfil(valores));
    } catch (e) {
      errorDelPerfil = motivoDe(e);
      throw e;
    }
  }

  async function subirEvidencia(archivo) {
    errorDeEvidencia = '';
    reservaPendiente = false;
    try {
      const respuesta = await consentimiento.cargarEvidencia(archivo);
      aplicarRespuesta(respuesta);
    } catch (e) {
      if (e?.cuerpo?.reserva_pendiente) reservaPendiente = true;
      else if (clasificar(e) === 'tiempo-agotado') {
        await actualizarRepresentante();
        if (estado?.representante?.estado === 'documento_recibido') return;
        errorDeEvidencia = 'La carga tardó demasiado y no pudimos confirmar si llegó. Comprueba su estado antes de enviarla otra vez.';
      } else errorDeEvidencia = motivoDe(e);
      throw e;
    }
  }

  async function descargarFormato() {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar formato para acudiente?',
      descripcion:'Se preparará el PDF de autorización para que tu representante pueda revisarlo y firmarlo.', confirmar:'Descargar PDF' })) return false;
    await consentimiento.descargarFormatoRepresentante();
    toast.descarga('Descargando formato de autorización en PDF.');
    return true;
  }

  async function actualizarVersiones() {
    try {
      versiones = await consentimiento.versiones();
      versionesNoDisponibles = false;
    } catch {
      versiones = null;
      versionesNoDisponibles = true;
    }
  }

  async function actualizarRepresentante() {
    if (refrescandoRepresentante || !sesion.autenticada) return;
    refrescandoRepresentante = true;
    try {
      const respuesta = await onboarding.estado();
      estado = respuesta;
      sesion.aplicarAcceso(
        respuesta.acceso,
        respuesta.tutoria_academica_sin_investigacion
      );
      if (respuesta.acceso === 'habilitado') navegar('/');
    } catch (e) {
      if (clasificar(e) === 'sin-sesion') await sesion.sincronizar();
    } finally {
      refrescandoRepresentante = false;
    }
  }

  async function decidir(decision) {
    errorDeDecision = '';
    sinVersionAlDecidir = false;
    motivoDeLaPolitica = '';
    alcancesFaltantes = [];
    avisoEnviado = null;
    try {
      const respuesta = await consentimiento.decidirConjunta(decision);
      avisoEnviado = decision === 'otorgado' ? (respuesta?.aviso_enviado ?? null) : null;
      aplicarRespuesta(respuesta);
    } catch (e) {
      const cual = e?.estadoDelServidor;
      if (cual === 'sin_version') {
        sinVersionAlDecidir = true;
        alcancesFaltantes = e?.cuerpo?.alcances_faltantes ?? [];
      } else if (cual === 'decision_ya_vigente' || cual === 'usar_revocacion') {
        motivoDeLaPolitica = e?.detalle || '';
        cargar();
      } else {
        errorDeDecision = motivoDe(e);
      }
      throw e;
    }
  }

  $effect(() => {
    sesion.autenticada;
    cargar();
  });

  $effect(() => {
    if (!sesion.autenticada || !representanteEsPasoActual) return;
    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') void actualizarVersiones();
    };
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    const intervalo = !versiones?.representante || versiones.representante.formato_disponible === false
      ? globalThis.setInterval(alVolver, 20_000)
      : null;
    return () => {
      if (intervalo !== null) globalThis.clearInterval(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  $effect(() => {
    const esperandoRevision =
      sesion.autenticada && estado?.representante?.estado === 'documento_recibido';
    if (!esperandoRevision) return;

    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') void actualizarRepresentante();
    };
    const intervalo = globalThis.setInterval(alVolver, 4_000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    return () => {
      globalThis.clearInterval(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  $effect(() => {
    const rechazado = estado?.representante?.estado === 'rechazado';
    if (rechazado && !rechazoAnunciado) {
      motivoDelRechazo = String(estado?.representante?.motivo ?? '').trim();
      dialogoDeRechazoAbierto = true;
      rechazoAnunciado = true;
    } else if (!rechazado) {
      rechazoAnunciado = false;
    }
  });
</script>

<section class="recorrido" class:modo-documento={Boolean(codigoDocumento)} class:modo-entrada={!sesion.autenticada && sesion.sincronizada}>
  <div class="tarjeta" class:tarjeta-documento={Boolean(codigoDocumento)} class:tarjeta-entrada={!sesion.autenticada && sesion.sincronizada} class:tarjeta-representante={representanteEsPasoActual}>
    <header class="encabezado">
      <div class="encabezado-superior">
        <div class="marca">
          <Icono nombre="escudo" medida={13} />
          <span>DidaxIa · Acceso y privacidad</span>
        </div>
        {#if sesion.autenticada && !codigoDocumento}
          <div class="salir-del-registro"><EntrarConGoogle /></div>
        {/if}
      </div>
      <h1>{titulo}</h1>
    </header>

    {#if !sesion.autenticada && sesion.sincronizada}
      <EntradaInstitucional />

    {:else if cargando || !sesion.sincronizada}
      <CargadorCubo mensaje="Comprobando tu estado…" />

    {:else if fallo}
      <Degradacion respuesta={fallo} alReintentar={cargar} />

    {:else if codigoDocumento}
      <div class="documento-independiente">
        <p class="aviso-documento">
          Esta copia se sirve sólo dentro de tu sesión y el servidor comprueba
          su huella antes de mostrarla. Puedes cerrar esta pestaña al terminar.
        </p>
        <DocumentoDeLaVersion codigo={codigoDocumento} rotulo="documento vigente" pagina />
      </div>

    {:else if representanteEsPasoActual}
      <PanelDelRepresentante
        representante={estado.representante}
        version={versiones?.representante ?? null}
        alDescargar={descargarFormato}
        alSubir={subirEvidencia}
        errorDelServidor={errorDeEvidencia}
        {reservaPendiente}
        motivo={estado.representante?.motivo ?? ''}
        {versionesNoDisponibles}
        alReintentarVersiones={actualizarVersiones}
        alComprobarEstado={actualizarRepresentante}
      />

    {:else if enBloqueo}

      <PanelDeEstado {acceso} alReintentar={cargar} />

      {#if bloqueoConSalida}
        <div class="salida-del-bloqueo">
          <p class="explica-salida">
            Puedes volver a decidir ahora. Se registrará como una decisión nueva
            y lo anterior se conserva: nada de lo que ya existe se borra.
          </p>
          <DecisionConjunta
            {esMenor}
            versionTitular={versiones?.titular ?? null}
            versionAsentimiento={versiones?.asentimiento ?? null}
            alDecidir={decidir}
            errorDelServidor={errorDeDecision}
            sinVersion={sinVersionAlDecidir}
            {alcancesFaltantes}
            {puedeAceptar}
            {puedeRechazar}
            {motivoDeLaPolitica}
          />
        </div>
      {/if}

    {:else if faltaPerfil}
      <FormularioDePerfil
        perfil={estado.perfil}
        {identidad}
        alGuardar={guardarPerfil}
        errorDelServidor={errorDelPerfil}
      />

    {:else if faltaDecision}

      <DecisionConjunta
        {esMenor}
        versionTitular={versiones?.titular ?? null}
        versionAsentimiento={versiones?.asentimiento ?? null}
        alDecidir={decidir}
        errorDelServidor={errorDeDecision}
        sinVersion={sinVersionAlDecidir}
        {alcancesFaltantes}
        {puedeAceptar}
        {puedeRechazar}
        {motivoDeLaPolitica}
      />

    {:else}

      <p class="paso-pendiente">
        Tu perfil y tu autorización están al día, pero el sistema todavía no
        habilita el tutor. Vuelve a comprobarlo en un momento; si sigue igual,
        avisa al equipo del proyecto.
      </p>
    {/if}



    {#if !representanteEsPasoActual}
      {#if avisoEnviado === true}
        <p class="aviso-correo" role="status">
          Tu decisión quedó guardada y te enviamos la confirmación a tu correo
          institucional.
        </p>
      {:else if avisoEnviado === false}
        <p class="aviso-correo sin-correo" role="status">
          Tu decisión quedó guardada. El correo de confirmación no pudo enviarse;
          la constancia sigue disponible en «Mis datos».
        </p>
      {/if}

      {#each recibos as unRecibo (unRecibo.alcance + unRecibo.secuencia)}
        <ReciboDelActo recibo={unRecibo} />
      {/each}
    {/if}


    {#if !representanteEsPasoActual}
      <div class="publicos">
        <p class="rotulo-publicos">Antes de decidir</p>
        <p class="nota-publicos">
          Estos textos explican qué información se prevé tratar, quién puede
          verla, para qué se utiliza y qué puedes pedir antes de decidir.
        </p>
        <EnlacesPublicos absolutos rotulo="Documentos públicos del proyecto" />
      </div>
    {/if}
    {#if sesion.autenticada && !codigoDocumento}
      <ReportarProblema compacto />
    {/if}
  </div>
</section>

{#if estado?.representante?.estado === 'rechazado'}
  <Dialogo bind:abierto={dialogoDeRechazoAbierto} titulo="Debes corregir la autorización">
    <div class="explicacion-rechazo">
      <p>El equipo investigador revisó el PDF y solicitó una corrección:</p>
      <blockquote>{motivoDelRechazo || 'Revisa el documento firmado antes de enviarlo de nuevo.'}</blockquote>
      <p>El intento anterior se conserva. Descarga el formato si lo necesitas y sube un PDF corregido para una nueva revisión.</p>
    </div>
    {#snippet acciones()}
      <Boton onclick={() => (dialogoDeRechazoAbierto = false)}>Entendido</Boton>
    {/snippet}
  </Dialogo>
{/if}

<style>
  .documento-independiente { display: flex; flex-direction: column; gap: 0.75rem; }
  .aviso-documento { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .recorrido {
    flex: 1;
    inline-size: 100%;
    min-block-size: 0;
    overflow-y: auto;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 16px 14px;
    background: var(--surface-canvas);
  }

  .tarjeta {
    display: flex;
    flex-direction: column;
    gap: 12px;
    inline-size: 100%;
    min-inline-size: 0;
    max-inline-size: 560px;
    background: var(--surface-panel);
    padding: 22px 24px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    box-sizing: border-box;
  }

  .recorrido.modo-documento { padding: clamp(12px, 2vw, 28px); }

  .tarjeta.tarjeta-documento {
    max-inline-size: 1080px;
    padding: clamp(18px, 3vw, 40px);
  }

  .tarjeta.tarjeta-entrada { max-inline-size: 920px; }
  .tarjeta.tarjeta-representante { max-inline-size: 620px; }

  .tarjeta-documento .documento-independiente {
    inline-size: 100%;
    max-inline-size: 900px;
    margin-inline: auto;
  }

  .encabezado { display: flex; flex-direction: column; gap: 4px; }
  .encabezado-superior { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .salir-del-registro { flex: none; }
  .salir-del-registro :global(.salir) { inline-size: auto; min-block-size: 36px; }

  .marca {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border-radius: var(--radius-pill);
    inline-size: fit-content;
  }

  h1 {
    margin: 4px 0 0;
    font-size: var(--texto-2xl);
    font-weight: 700;
    color: var(--ink-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  .salida-del-bloqueo {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-block-start: 12px;
    border-block-start: 1px solid var(--ink-ghost);
  }

  .explica-salida {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .paso-pendiente {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .explicacion-rechazo { display: grid; gap: 10px; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .explicacion-rechazo p { margin: 0; }
  .explicacion-rechazo blockquote {
    margin: 0;
    padding: 10px 12px;
    border-inline-start: 3px solid var(--semantic-warning);
    border-radius: var(--radius-xs);
    background: var(--surface-panel);
    color: var(--ink-primary);
  }

  .aviso-correo {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--accent-main);
    border-radius: var(--radius-xs);
  }

  .aviso-correo.sin-correo { border-inline-start-color: var(--ink-tertiary); }

  .publicos {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-block-start: 12px;
    border-block-start: 1px solid var(--ink-ghost);
  }

  .rotulo-publicos {
    margin: 0;
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .nota-publicos {
    margin: 0;
    font-size: var(--texto-xs);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  @media (max-width: 75rem) {
    .recorrido { padding: 12px 10px; }
    .tarjeta { padding: 18px 16px; }
  }

  @media (max-width: 75rem) {
    .encabezado-superior { align-items: stretch; flex-direction: column; }
    .salir-del-registro :global(.salir) { inline-size: 100%; }
  }
</style>
