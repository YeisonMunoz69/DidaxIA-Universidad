import { normalizar } from './catalogo.js';

export function crearProgreso() {
  let fases = $state([]);
  let activo = $state(false);

  return {
    get fases() { return fases; },
    get activo() { return activo; },

    get actual() { return fases.length ? fases[fases.length - 1] : null; },

    get cumplidas() { return fases.slice(0, -1); },

    iniciar() {
      fases = [];
      activo = true;
    },

    recibir(recibida) {
      const f = normalizar(recibida);
      if (!f) return false;
      if (fases.length && fases[fases.length - 1].id === f.id) {
        fases = [...fases.slice(0, -1), f];
        return true;
      }
      fases = [...fases, f];
      return true;
    },

    terminar() { activo = false; },

    limpiar() { fases = []; activo = false; }
  };
}
