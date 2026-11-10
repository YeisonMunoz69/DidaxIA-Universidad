/**
 * Estado compartido del historial · como en el mockup, no una pantalla aparte.
 *
 * `pc.html`/`movil.html` no navegan a un «/historial»: la barra lateral
 * lista las sesiones y un clic sustituye lo que se ve en el mismo sitio,
 * como en cualquier interfaz conversacional. Esto es lo que conecta esa
 * lista (en `Aplicacion.svelte`, dentro del carril) con lo que pinta la
 * conversación (`Conversacion.svelte`), sin que uno importe al otro — el
 * mismo patrón que `sesion.svelte.js` y `preferencias.svelte.js`: una
 * instancia compartida con getters, en vez de una prop que tendría que
 * atravesar el enrutado dinámico (`{@const Pantalla = modulo.default}` no
 * pasa props hoy, y no debería aprenderlas solo para esto).
 *
 * SE PUEDE ESCRIBIR SOBRE UN HILO PASADO, Y AHORA SE ARCHIVA DE VERDAD.
 * Hasta que se sumó `retomar_sesion` al contrato de `POST /api/turno`
 * (`rutas/turno.py::contexto_retomado`), esto era de solo lectura: el
 * contrato no ofrecía continuar una sesión antigua, vivía en memoria del
 * proceso. Ahora el primer turno de cada retoma siembra esa memoria desde
 * Postgres y CADA turno de la retoma —no solo el primero— viaja con
 * `retomar_sesion` para archivarse bajo la conversación que se está viendo
 * y no bajo la sesión en vivo. Ver `Conversacion.svelte::enviar`.
 *
 * `sesionVista` se guarda en `sessionStorage` por la misma razón que
 * `conversacion.svelte.js` guarda el hilo en vivo: recargar la página no
 * debería devolver a quien estaba retomando un hilo pasado al hilo en
 * vivo sin avisar. `recuperarSiHaceFalta()` es quien vuelve a pedir el
 * contenido cuando `sesionVista` llega así, ya con sesión pero sin
 * `hiloVisto` —ver `Aplicacion.svelte`.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md §13
 */
import * as api from '../api/historial.js';
import { describir } from '../errores/degradacion.js';
import { conversacion } from '../conversacion/conversacion.svelte.js';

/** `sistema` en el contrato de historial; `tutor` en el resto del árbol. */
function autorDelHilo(autor) {
  return autor === 'estudiante' ? 'estudiante' : 'tutor';
}

/**
 * Un mensaje del historial → `{ autor, degradado, turno }`, la forma que
 * `hilo` ya usa en `Conversacion.svelte`.
 *
 * Sin `bloques` pasa en dos casos, y `§13.2` los distingue con `degradado`:
 * el mensaje del estudiante —se reconstruye como un bloque de prosa suelto,
 * igual que `enviar()` arma el turno en vivo— y el aviso de una degradación
 * archivada, que NO es una afirmación del tutor y por eso no pasa por
 * `Turno.svelte`/`SelloVerificacion` en absoluto —`Conversacion.svelte` la
 * pinta con `Degradacion`, igual que cualquier degradación del hilo vivo—.
 * Meterla en un bloque de prosa sellado es lo que hacía que el historial
 * mostrara «Estado de verificación no reconocido» sobre el propio aviso de
 * fallo, detectado el 2026-08-22 al sembrar una conversación degradada.
 */
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

/** Qué conversación pasada se está viendo —y quizás retomando—, si alguna. */
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
  let listaCargada = false; // no reactivo: solo evita repetir la petición
  let falloLista = $state(null);

  // No reactivo: solo coordina llamadas a `cargarLista()` que se solapan.
  let refrescoPendiente = false;

  let sesionVista = $state(leerSesionVistaGuardada());
  let hiloVisto = $state(null);
  let cargandoHilo = $state(false);
  let falloHilo = $state(null);
  /**
   * ¿El próximo turno que se escriba aquí todavía no le sembró memoria real
   * al backend? Se enciende al abrir un hilo pasado de verdad —no la
   * reconstrucción `local-`, que no tiene fila que retomar— y se apaga tras
   * el primer envío exitoso: de ahí en adelante la sesión en vivo ya
   * construye sobre lo que ese primer turno dejó escrito. Ver
   * `Conversacion.svelte::enviar` y `rutas/turno.py::contexto_retomado`.
   */
  let necesitaRetomar = $state(false);

  /**
   * Pide la lista una sola vez por sesión de la aplicación —salvo que se
   * fuerce—.
   *
   * Un `forzar` que llega mientras OTRA petición ya está en vuelo no se
   * pierde: se apunta en `refrescoPendiente` y la petición en curso, al
   * terminar, vuelve a pedir antes de soltar `cargandoLista`. Sin esto,
   * `Conversacion.svelte::enviar` pidiendo refrescar justo mientras el
   * `onMount` de la barra lateral todavía estaba cargando la lista por
   * primera vez hacía que ese refresco se descartara en silencio —el
   * carril se quedaba con la lista de antes de escribir el mensaje—.
   */
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

  /** Ver una sesión pasada. Sustituye lo que `Conversacion.svelte` pinta. */
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
        // La reconstrucción `local-` no tiene fila en el backend que
        // retomar; una sesión de verdad sí, y por eso solo esta rama lo
        // enciende.
        necesitaRetomar = true;
      }
    } catch (e) {
      falloHilo = describir(e);
    } finally {
      cargandoHilo = false;
    }
  }

  /** Añade un turno al hilo pasado que se está viendo —y ahora escribiendo. */
  function agregarAlHiloVisto(autor, turno) {
    hiloVisto = [...(hiloVisto ?? []), { autor, turno }];
  }

  /** El primer turno de esta retoma ya le sembró memoria real al backend. */
  function marcarRetomado() {
    necesitaRetomar = false;
  }

  /** Volver a la conversación en vivo. */
  function volver() {
    sesionVista = null;
    guardarSesionVista(null);
    hiloVisto = null;
    falloHilo = null;
    necesitaRetomar = false;
  }

  /** Limpiar todo el estado de historial al cerrar sesión */
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

  /**
   * Recarga el contenido de `sesionVista` cuando llegó de `sessionStorage`
   * —una recarga de página (F5)— y todavía no tiene `hiloVisto`.
   *
   * Sin esto, `sesionVista` sobrevive a la recarga pero `hiloVisto` no
   * —vive solo en memoria, nunca se guardó—, y el carril marcaba la
   * conversación como activa mientras el panel de chat se quedaba vacío
   * hasta que se hacía clic de nuevo en la lista. Se llama desde
   * `Aplicacion.svelte` junto con `cargarLista()`, una vez hay sesión.
   */
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

/** La instancia que usa la aplicación. Una sola, como `sesion` y `preferencias`. */
export const historial = crearHistorial();
