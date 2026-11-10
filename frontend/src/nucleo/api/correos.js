import { pedir } from './cliente.js';

const RUTA = '/investigacion/correos';

export function listarPlantillas({ señal } = {}) {
  return pedir(`${RUTA}/plantillas`, { señal });
}

export function previsualizar(cuerpo, { señal } = {}) {
  return pedir(`${RUTA}/vista-previa`, { metodo: 'POST', cuerpo, señal });
}

export function enviar(cuerpo, { señal } = {}) {
  return pedir(`${RUTA}/enviar`, {
    metodo: 'POST',
    cuerpo,
    señal,
    espera: 200_000
  });
}
