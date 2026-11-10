/** Comunicación saliente iniciada por un investigador desde «Mi perfil». */
import { pedir } from './cliente.js';

const RUTA = '/investigacion/correos';

export function listarPlantillas({ señal } = {}) {
  return pedir(`${RUTA}/plantillas`, { señal });
}

/** Render del mismo armazón del envío; no contacta al proveedor. */
export function previsualizar(cuerpo, { señal } = {}) {
  return pedir(`${RUTA}/vista-previa`, { metodo: 'POST', cuerpo, señal });
}

export function enviar(cuerpo, { señal } = {}) {
  return pedir(`${RUTA}/enviar`, {
    metodo: 'POST',
    cuerpo,
    señal,
    // Hasta 35 copias con plazo de cinco segundos y separación entre copias.
    espera: 200_000
  });
}
