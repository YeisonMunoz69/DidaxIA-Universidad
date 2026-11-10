/**
 * Estado de la progresión del turno en curso.
 *
 * Qué fase va, cuáles se cumplieron y cuándo se limpia.
 *
 * Las fases se ACUMULAN en lugar de sustituirse. Al terminar el turno se lee
 * el recorrido completo, que es lo que distingue esto de un simple indicador
 * de espera: si el turno falla, la última fase alcanzada dice dónde se quedó,
 * y RP-17 puede ser específico en vez de genérico.
 *
 * Toda fase pasa por `normalizar()`, así que una fase fuera del catálogo no
 * llega nunca a este estado.
 *
 */
import { normalizar } from './catalogo.js';

export function crearProgreso() {
  /** @type {{id: string, texto: string}[]} */
  let fases = $state([]);
  let activo = $state(false);

  return {
    get fases() { return fases; },
    get activo() { return activo; },

    /** La fase en curso es la última recibida. */
    get actual() { return fases.length ? fases[fases.length - 1] : null; },

    /** Las ya cumplidas son todas menos la última. */
    get cumplidas() { return fases.slice(0, -1); },

    /** Comienza un turno. Limpia lo del anterior. */
    iniciar() {
      fases = [];
      activo = true;
    },

    /**
     * Registra una fase del servidor. Devuelve si se aceptó.
     * Una fase fuera del catálogo se descarta en silencio para el usuario,
     * pero el retorno permite que la prueba de contrato lo detecte.
     *
     * REPETIR LA FASE EN CURSO NO AÑADE UN PASO. El servidor emite una fase
     * por filtro y dos filtros distintos comparten fase a propósito —la
     * verificación simbólica y el juicio complementario son los dos
     * «comprobando»—, así que la misma llega dos veces seguidas. Pintarla dos
     * veces le enseñaba al estudiante «Comprobando cada afirmación ·
     * Comprobando cada afirmación», visto en el navegador el 2026-08-11: dos
     * pasos donde hay uno. Se acepta igual —es una fase válida— pero no
     * inventa un paso que `DD-11` no declara.
     */
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

    /** Termina el turno. Las fases se conservan por si hubo degradación. */
    terminar() { activo = false; },

    /** Limpia del todo, al empezar una conversación nueva. */
    limpiar() { fases = []; activo = false; }
  };
}
