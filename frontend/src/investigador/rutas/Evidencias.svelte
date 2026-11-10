
<script>
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import ColaDeEvidencias from '../piezas/ColaDeEvidencias.svelte';
  import DetalleDeEvidencia from '../piezas/DetalleDeEvidencia.svelte';
  import DialogoDeAprobacion from '../piezas/DialogoDeAprobacion.svelte';
  import DialogoDeRechazo from '../piezas/DialogoDeRechazo.svelte';
  import EstadoVacio from '../../docente/piezas/EstadoVacio.svelte';
  import * as api from '../../nucleo/api/evidencias.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { untrack } from 'svelte';

  let filtro = $state(api.FILTRO_POR_DEFECTO);
  let evidencias = $state([]);
  let cursor = $state(null);
  let hayMas = $state(false);
  let cargandoCola = $state(false);
  let falloCola = $state(null);

  let seleccionada = $state(0);
  let detalle = $state(null);
  let documento = $state(null);
  let detalleDe = $state(0);
  let documentoDe = $state(0);
  let cargandoDetalle = $state(false);
  let cargandoArchivo = $state(false);
  let falloDetalle = $state(null);
  let falloArchivo = $state(null);
  let recibo = $state(null);

  let aprobacionAbierta = $state(false);
  let rechazoAbierto = $state(false);
  let resolviendo = $state(false);
  let decidiendoSobre = $state(0);

  let generacionCola = 0;
  let generacionSeleccion = 0;
  let controlCola = null;
  let controlSeleccion = null;

  const colaVigente = (generacion, estado) =>
    generacion === generacionCola && estado === filtro;

  const seleccionVigente = (generacion) => generacion === generacionSeleccion;

  let viendoDetalleEnMovil = $state(false);

  function nuevaPeticionDeCola() {
    controlCola?.abort();
    controlCola = new AbortController();
    return { generacion: ++generacionCola, señal: controlCola.signal };
  }

  async function cargarCola() {
    const estado = filtro;
    const { generacion, señal } = nuevaPeticionDeCola();
    cargandoCola = true;
    falloCola = null;
    try {
      const pagina = await api.listar({ estado, señal });
      if (!colaVigente(generacion, estado)) return;
      evidencias = pagina.evidencias;
      cursor = pagina.cursorSiguiente;
      hayMas = pagina.hayMas;
    } catch (e) {
      if (!colaVigente(generacion, estado)) return;
      evidencias = [];
      cursor = null;
      hayMas = false;
      falloCola = describir(e);
    } finally {
      if (colaVigente(generacion, estado)) cargandoCola = false;
    }
  }

  async function cargarMas() {
    if (!cursor || cargandoCola) return;
    const estado = filtro;
    const desde = cursor;
    const { generacion, señal } = nuevaPeticionDeCola();
    cargandoCola = true;
    try {
      const pagina = await api.listar({ estado, cursor: desde, señal });
      if (!colaVigente(generacion, estado) || cursor !== desde) return;
      evidencias = [...evidencias, ...pagina.evidencias];
      cursor = pagina.cursorSiguiente;
      hayMas = pagina.hayMas;
    } catch (e) {
      if (!colaVigente(generacion, estado) || cursor !== desde) return;
      falloCola = describir(e);
    } finally {
      if (colaVigente(generacion, estado)) cargandoCola = false;
    }
  }

  function reiniciarSeleccion(id) {
    controlSeleccion?.abort();
    controlSeleccion = new AbortController();
    seleccionada = id;
    detalle = null;
    detalleDe = 0;
    documento = null;
    documentoDe = 0;
    falloDetalle = null;
    falloArchivo = null;
    cargandoDetalle = false;
    cargandoArchivo = false;
    recibo = null;
    cerrarDialogos();
    return ++generacionSeleccion;
  }

  async function seleccionar(id) {
    const generacion = reiniciarSeleccion(id);
    const señal = controlSeleccion?.signal;
    viendoDetalleEnMovil = true;

    cargandoDetalle = true;
    try {
      const abierta = await api.detalle(id, { señal });
      if (!seleccionVigente(generacion)) return;
      detalle = abierta;
      detalleDe = id;
    } catch (e) {
      if (!seleccionVigente(generacion)) return;
      falloDetalle = describir(e);
      return;
    } finally {
      if (seleccionVigente(generacion)) cargandoDetalle = false;
    }

    await cargarArchivo(id, generacion, señal);
  }

  async function cargarArchivo(id, generacion, señal) {
    cargandoArchivo = true;
    falloArchivo = null;
    try {
      const bytes = await api.archivo(id, { señal });
      if (!seleccionVigente(generacion)) return;
      documento = bytes;
      documentoDe = id;
    } catch (e) {
      if (!seleccionVigente(generacion)) return;
      documento = null;
      documentoDe = 0;
      falloArchivo = describir(e);
    } finally {
      if (seleccionVigente(generacion)) cargandoArchivo = false;
    }
  }

  function reintentarArchivo() {
    const id = seleccionada;
    if (!id || detalleDe !== id) return;
    controlSeleccion?.abort();
    controlSeleccion = new AbortController();
    void cargarArchivo(id, ++generacionSeleccion, controlSeleccion.signal);
  }

  function cerrarDialogos() {
    aprobacionAbierta = false;
    rechazoAbierto = false;
    decidiendoSobre = 0;
  }

  function abrirDecision(cual) {
    const id = idDecidible;
    if (!id) return;
    decidiendoSobre = id;
    if (cual === 'aprobar') aprobacionAbierta = true;
    else rechazoAbierto = true;
  }

  async function resolver(id, accion, tipo) {
    if (resolviendo) return;
    if (!id || id !== idDecidible) {
      cerrarDialogos();
      return;
    }
    const generacion = generacionSeleccion;
    const señal = controlSeleccion?.signal;
    resolviendo = true;
    try {
      const respuesta = await accion(id);
      (tipo === 'aprobar' ? toast.exito : toast.error)(tipo === 'aprobar'
        ? 'Autorización aprobada por doble custodia.' : 'Autorización devuelta para corrección.');
      cerrarDialogos();
      if (seleccionVigente(generacion) && seleccionada === id) {
        recibo = respuesta;
        try {
          const fresco = await api.detalle(id, { señal });
          if (seleccionVigente(generacion) && seleccionada === id) {
            detalle = fresco;
            detalleDe = id;
          }
        } catch {
        }
      }
      await cargarCola();
    } catch (e) {
      cerrarDialogos();
      if (!seleccionVigente(generacion) || seleccionada !== id) return;
      falloDetalle = describir(e);
    } finally {
      resolviendo = false;
    }
  }

  $effect(() => {
    void filtro;
    untrack(() => {
      reiniciarSeleccion(0);
      viendoDetalleEnMovil = false;
      cargarCola();
    });
  });

  $effect(() => () => {
    controlCola?.abort();
    controlSeleccion?.abort();
    generacionCola += 1;
    generacionSeleccion += 1;
  });

  const detalleVigente = $derived(
    detalleDe !== 0 && detalleDe === seleccionada ? detalle : null
  );

  const documentoVigente = $derived(
    documento !== null && documentoDe !== 0 && documentoDe === seleccionada && documentoDe === detalleDe
      ? documento
      : null
  );

  const idDecidible = $derived(
    seleccionada !== 0 &&
    detalleVigente?.estado === 'pendiente' &&
    documentoVigente !== null &&
    !cargandoArchivo
      ? seleccionada
      : 0
  );
</script>

<PantallaDesplazable anchoMaximo="min(90rem, 100%)">
  <CabeceraDeRuta
    titulo="Autorizaciones de representantes"
    icono="evidencias-institucionales"
    insignia="Revisión de evidencia">
    {#snippet nota()}
      Cada autorización se revisa <strong>después de abrir el documento</strong>.
      Los botones de decisión permanecen cerrados mientras no se haya podido
      recuperar el archivo.
    {/snippet}
  </CabeceraDeRuta>

  <div class="maestro-detalle" class:viendo-detalle={viendoDetalleEnMovil}>
    <div class="columna-cola">
      <ColaDeEvidencias
        {evidencias}
        bind:filtro
        {seleccionada}
        cargando={cargandoCola}
        {hayMas}
        fallo={falloCola}
        alSeleccionar={seleccionar}
        alCargarMas={cargarMas}
        alReintentar={cargarCola} />
    </div>

    <div class="columna-detalle">
      {#if seleccionada}

        <DetalleDeEvidencia
          detalle={detalleVigente}
          documento={documentoVigente}
          {cargandoDetalle}
          {cargandoArchivo}
          {falloDetalle}
          {falloArchivo}
          {resolviendo}
          {recibo}
          alVolver={() => { viendoDetalleEnMovil = false; }}
          alReintentarArchivo={reintentarArchivo}
          alAprobar={() => abrirDecision('aprobar')}
          alRechazar={() => abrirDecision('rechazar')} />
      {:else}
        <EstadoVacio
          icono="datos"
          texto="Elija una autorización de la lista para revisarla."
          tono="neutro" />
      {/if}
    </div>
  </div>
</PantallaDesplazable>


<DialogoDeAprobacion
  bind:abierto={aprobacionAbierta}
  intento={detalleVigente?.intento ?? 0}
  enviando={resolviendo}
  alConfirmar={() => resolver(decidiendoSobre, (id) => api.aprobar(id), 'aprobar')}
  alCancelar={cerrarDialogos} />

<DialogoDeRechazo
  bind:abierto={rechazoAbierto}
  intento={detalleVigente?.intento ?? 0}
  enviando={resolviendo}
  alConfirmar={(motivo) => resolver(decidiendoSobre, (id) => api.rechazar(id, motivo), 'rechazar')}
  alCancelar={cerrarDialogos} />

<style>
  .maestro-detalle {
    display: grid;
    grid-template-columns: minmax(20rem, 26rem) minmax(0, 1fr);
    gap: var(--espacio-lg);
    align-items: start;
    min-inline-size: 0;
  }

  .columna-cola,
  .columna-detalle { min-inline-size: 0; }

  @media (max-width: 60rem) {
    .maestro-detalle { grid-template-columns: minmax(0, 1fr); }

    .maestro-detalle.viendo-detalle .columna-cola { display: none; }
    .maestro-detalle:not(.viendo-detalle) .columna-detalle { display: none; }
  }
</style>
