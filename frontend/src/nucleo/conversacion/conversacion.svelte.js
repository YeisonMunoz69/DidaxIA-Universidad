
const CLAVE_HILO_ACTIVO = 'didaxia_hilo_activo_v2';

const CLAVE_DUENO_HILO = 'didaxia_dueno_hilo_v2';

export function crearConversacion() {
  let hilo = $state(leerHiloGuardado());
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

    agregarTurno(autor, turno) {
      const nuevoTurno = { autor, turno };
      hilo = [...hilo, nuevoTurno];
      guardarHiloActivo(hilo);
    },

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
