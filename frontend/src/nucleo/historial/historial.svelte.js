import * as api from '../api/historial.js';
import { describir } from '../errores/degradacion.js';
import { conversacion } from '../conversacion/conversacion.svelte.js';

function autorDelHilo(autor) {
  return autor === 'estudiante' ? 'estudiante' : 'tutor';
}

function mensajeAHilo(m) {
  const degradado = Boolean(m?.degradado);
  return {
    autor: autorDelHilo(m?.autor),
    degradado,
    contenido: m?.contenido ?? '',
    turno: {
      turno: m?.turno ?? '',
      bloques: degradado ? [] : (m?.bloques ?? [{ tipo: 'prosa', contenido: m?.contenido ?? '' }]),
      citas: m?.citas,
      nivel: m?.nivel,
      procedencia: m?.procedencia
    }
  };
}

const CLAVE_SESION_VISTA = 'didaxia_viendo_historial_v1';

function leerSesionVistaGuardada() {
  try {
    if (typeof window === 'undefined') return null;
    return window.sessionStorage?.getItem(CLAVE_SESION_VISTA) ?? null;
  } catch {
    return null;
  }
}

function guardarSesionVista(sesion) {
  try {
    if (typeof window === 'undefined') return;
    if (sesion) window.sessionStorage?.setItem(CLAVE_SESION_VISTA, sesion);
    else window.sessionStorage?.removeItem(CLAVE_SESION_VISTA);
  } catch {}
}

export function crearHistorial() {
  let conversaciones = $state([]);
  let cargandoLista = $state(false);
  let listaCargada = false;
  let falloLista = $state(null);

  let refrescoPendiente = false;

  let sesionVista = $state(leerSesionVistaGuardada());
  let hiloVisto = $state(null);
  let cargandoHilo = $state(false);
  let falloHilo = $state(null);
  let necesitaRetomar = $state(false);

  async function cargarLista(forzar = false) {
    if (forzar) refrescoPendiente = true;
    if (cargandoLista) return;
    if (listaCargada && !refrescoPendiente) return;

    cargandoLista = true;
    do {
      refrescoPendiente = false;
      falloLista = null;
      try {
        const r = await api.listar();
        conversaciones = r?.conversaciones ?? [];
        listaCargada = true;
      } catch (e) {
        falloLista = describir(e);
      }
    } while (refrescoPendiente);
    cargandoLista = false;
  }

  async function recargarLista() {
    return cargarLista(true);
  }

  async function ver(sesion) {
    sesionVista = sesion;
    guardarSesionVista(sesion);
    hiloVisto = null;
    falloHilo = null;
    cargandoHilo = true;
    necesitaRetomar = false;
    try {
      if (typeof sesion === 'string' && sesion.startsWith('local-')) {
        const itemLocal = conversacion.historialLocal.find((h) => h.sesion === sesion);
        if (itemLocal) {
          hiloVisto = itemLocal.mensajes ?? [];
        } else {
          throw new Error('Conversación guardada no encontrada');
        }
      } else {
        const r = await api.leer(sesion);
        hiloVisto = (r?.mensajes ?? []).map(mensajeAHilo);
        necesitaRetomar = true;
      }
    } catch (e) {
      falloHilo = describir(e);
    } finally {
      cargandoHilo = false;
    }
  }

  function agregarAlHiloVisto(autor, turno) {
    hiloVisto = [...(hiloVisto ?? []), { autor, turno }];
  }

  function marcarRetomado() {
    necesitaRetomar = false;
  }

  function volver() {
    sesionVista = null;
    guardarSesionVista(null);
    hiloVisto = null;
    falloHilo = null;
    necesitaRetomar = false;
  }

  function limpiar() {
    conversaciones = [];
    listaCargada = false;
    cargandoLista = false;
    falloLista = null;
    sesionVista = null;
    guardarSesionVista(null);
    hiloVisto = null;
    cargandoHilo = false;
    falloHilo = null;
    necesitaRetomar = false;
  }

  async function recuperarSiHaceFalta() {
    if (sesionVista && hiloVisto === null && !cargandoHilo) {
      await ver(sesionVista);
    }
  }

  return {
    get conversaciones() { return conversaciones; },
    get cargandoLista() { return cargandoLista; },
    get falloLista() { return falloLista; },

    get sesionVista() { return sesionVista; },
    get viendoHistorial() { return sesionVista !== null; },
    get hiloVisto() { return hiloVisto; },
    get cargandoHilo() { return cargandoHilo; },
    get falloHilo() { return falloHilo; },
    get necesitaRetomar() { return necesitaRetomar; },

    cargarLista,
    recargarLista,
    ver,
    volver,
    limpiar,
    agregarAlHiloVisto,
    marcarRetomado,
    recuperarSiHaceFalta
  };
}

export const historial = crearHistorial();
