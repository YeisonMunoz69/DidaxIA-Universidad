import { esEstudiante } from '../nucleo/sesion/rol.js';

export const ESPACIO_TUTOR = 'tutor';

export const ESPACIO_PROFESIONAL = 'profesional';

export const ESPACIOS = Object.freeze([ESPACIO_TUTOR, ESPACIO_PROFESIONAL]);

export function espaciosDe(rol) {
  if (esEstudiante(rol)) return [ESPACIO_TUTOR];
  return [ESPACIO_PROFESIONAL, ESPACIO_TUTOR];
}

export function puedeElegirEspacio(rol) {
  return espaciosDe(rol).length > 1;
}

export function espacioPredeterminadoDe(rol) {
  return espaciosDe(rol)[0];
}

export function espacioValido(espacio, rol) {
  return espaciosDe(rol).includes(espacio);
}

export function normalizarEspacio(espacio, rol) {
  return espacioValido(espacio, rol) ? espacio : espacioPredeterminadoDe(rol);
}

export function arbolDe(rol, espacio) {
  return normalizarEspacio(espacio, rol) === ESPACIO_PROFESIONAL
    ? 'no-estudiante'
    : 'estudiante';
}
