import {
  ESPACIO_PROFESIONAL,
  ESPACIO_TUTOR,
  espacioValido,
  normalizarEspacio,
  puedeElegirEspacio
} from '../../enrutado/espacios.js';
import { inicioDe } from '../../enrutado/caminos.js';
import { sesion } from '../sesion/sesion.svelte.js';

const CLAVE = 'agente-calculo.espacio';

function leerGuardado() {
  try {
    return globalThis.localStorage?.getItem(CLAVE) ?? '';
  } catch {
    return '';
  }
}

export function crearEspacio() {
  let elegido = $state(leerGuardado());

  let ultimoProfesional = $state('');

  return {
    get activo() {
      return normalizarEspacio(elegido, sesion.rol);
    },

    get esTutor() {
      return this.activo === ESPACIO_TUTOR;
    },

    get esProfesional() {
      return this.activo === ESPACIO_PROFESIONAL;
    },

    get puedeElegir() {
      return puedeElegirEspacio(sesion.rol);
    },

    destinoDe(espacio) {
      const valido = normalizarEspacio(espacio, sesion.rol);
      if (valido === ESPACIO_PROFESIONAL && ultimoProfesional) return ultimoProfesional;
      return inicioDe(sesion.rol, valido);
    },

    recordarProfesional(camino) {
      if (typeof camino === 'string' && camino) ultimoProfesional = camino;
    },

    get ultimoDestinoProfesional() {
      return ultimoProfesional;
    },

    elegir(espacio) {
      if (!espacioValido(espacio, sesion.rol)) return;
      elegido = espacio;
      try {
        globalThis.localStorage?.setItem(CLAVE, espacio);
      } catch {
      }
    }
  };
}

export const espacio = crearEspacio();
