import { inicioDe } from './caminos.js';
import { puedeAbrir, rutaDe } from './rutas.js';
import { esEstudiante } from '../nucleo/sesion/rol.js';
import { alcanzable, destinoDe, SIN_CONSULTAR } from '../nucleo/sesion/acceso.js';

export { arbolDe, navegar } from './navegar.js';

export function resolver(pedido, quien) {
  const ruta = rutaDe(pedido);

  if (!ruta) return pedido;

  if (!puedeAbrir(ruta, quien?.rol, quien?.espacio)) {
    return inicioDe(quien?.rol, quien?.espacio);
  }

  if (esEstudiante(quien?.rol)) {
    const acceso = quien?.autenticada === false ? SIN_CONSULTAR : (quien?.acceso ?? SIN_CONSULTAR);
    if (!alcanzable(pedido, acceso, quien?.tutoriaAcademicaSinInvestigacion)) {
      return destinoDe(acceso);
    }
  }

  return ruta.redirigirA ?? pedido;
}

export function redirige(pedido, quien) {
  return resolver(pedido, quien) !== pedido;
}
