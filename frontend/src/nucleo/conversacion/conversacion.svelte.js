/**
 * Estado reactivo de la conversación activa.
 *
 * Mantiene el hilo de diálogo del estudiante con el tutor activo durante la
 * navegación entre rutas (e.g. `/conceptos`, `/unirse`, `/mis-datos`) y recargas
 * mediante `sessionStorage`. Toda la persistencia histórica reside exclusivamente
 * en la base de datos PostgreSQL en el servidor.
 */

/**
 * `_v2`: la forma de `turno`/`bloques` cambia con el contrato
 * (`08-Contrato-del-Turno.md`) y no con un lanzamiento del frontend, así que
 * no hay forma de saber desde aquí si lo que quedó en `sessionStorage` de una
 * pestaña abierta antes del último cambio sigue siendo válido. Subir este
 * número invalida —sin migración, sin intentar interpretarlo— cualquier hilo
 * guardado con la forma anterior; es lo mismo que ya hace `limpiar()`, solo
 * que también alcanza a quien no cerró sesión, no recargó, y se quedó con la
 * pestaña abierta de un día para otro.
 */
const CLAVE_HILO_ACTIVO = 'didaxia_hilo_activo_v2';

/**
 * De qué `sesion.conversacion` es el hilo que hay en `CLAVE_HILO_ACTIVO`.
 *
 * `sesiones.py` vive en memoria del proceso: un reinicio del backend pierde
 * todas las sesiones, pero la cookie sigue en el navegador y `GET /api/sesion`
 * responde abriendo una anónima NUEVA con un identificador distinto —sin
 * error que avisar, es el comportamiento correcto de esa ruta—. Sin este
 * dueño guardado, `sessionStorage` (que sobrevive a recargar la página, a
 * diferencia del estado en memoria de este módulo) seguiría ofreciendo el
 * hilo de una conversación que el servidor ya olvidó.
 */
const CLAVE_DUENO_HILO = 'didaxia_dueno_hilo_v2';

export function crearConversacion() {
  let hilo = $state(leerHiloGuardado());
  // Solo en memoria: posición de presentación, nunca una segunda copia del chat.
  let posicionLectura = null;

  function leerHiloGuardado() {
    try {
      if (typeof window === 'undefined') return [];
      const guardado = window.sessionStorage?.getItem(CLAVE_HILO_ACTIVO);
      return guardado ? JSON.parse(guardado) : [];
    } catch {
      return [];
    }
  }

  function guardarHiloActivo(nuevoHilo) {
    try {
      if (typeof window !== 'undefined') {
        window.sessionStorage?.setItem(CLAVE_HILO_ACTIVO, JSON.stringify(nuevoHilo));
      }
    } catch {}
  }

  function leerDuenoGuardado() {
    try {
      if (typeof window === 'undefined') return null;
      return window.sessionStorage?.getItem(CLAVE_DUENO_HILO) ?? null;
    } catch {
      return null;
    }
  }

  function guardarDueno(identificadorSesion) {
    try {
      if (typeof window === 'undefined') return;
      if (identificadorSesion) {
        window.sessionStorage?.setItem(CLAVE_DUENO_HILO, identificadorSesion);
      } else {
        window.sessionStorage?.removeItem(CLAVE_DUENO_HILO);
      }
    } catch {}
  }

  return {
    get hilo() {
      return hilo;
    },
    get vacia() {
      return hilo.length === 0;
    },
    get historialLocal() {
      return [];
    },
    recordarLectura(clave, posicion, longitud) {
      posicionLectura = { clave, posicion, longitud };
    },
    recuperarLectura(clave, longitud) {
      const guardada = posicionLectura;
      posicionLectura = null;
      return guardada?.clave === clave && guardada.longitud === longitud ? guardada.posicion : null;
    },

    /** Agrega un turno al hilo activo */
    agregarTurno(autor, turno) {
      const nuevoTurno = { autor, turno };
      hilo = [...hilo, nuevoTurno];
      guardarHiloActivo(hilo);
    },

    /** Purga todo el estado de conversación */
    limpiar() {
      posicionLectura = null;
      hilo = [];
      guardarHiloActivo([]);
      try {
        if (typeof window !== 'undefined') {
          window.sessionStorage?.removeItem(CLAVE_HILO_ACTIVO);
          window.sessionStorage?.removeItem(CLAVE_DUENO_HILO);
          window.localStorage?.removeItem('didaxia_historial_local');
        }
      } catch {}
    },

    /**
     * Confirma —o descarta— el hilo cacheado según de qué sesión es de
     * verdad. Se llama con cada respuesta de `GET /api/sesion`, incluida la
     * primera de la pestaña: `sessionStorage` sobrevive a una recarga, así
     * que comparar contra el estado en memoria de este módulo no basta —
     * arranca en blanco en cada carga—. Comparar contra lo que quedó
     * guardado junto al propio hilo sí distingue «sigo siendo la misma
     * sesión» de «el servidor me dio otra sin avisar».
     */
    verificarDueno(identificadorSesion) {
      const duenoGuardado = leerDuenoGuardado();
      if (duenoGuardado && identificadorSesion && duenoGuardado !== identificadorSesion) {
        posicionLectura = null;
        hilo = [];
        try {
          if (typeof window !== 'undefined') {
            window.sessionStorage?.removeItem(CLAVE_HILO_ACTIVO);
          }
        } catch {}
      }
      guardarDueno(identificadorSesion || null);
    }
  };
}

export const conversacion = crearConversacion();
