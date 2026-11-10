import { RUTAS, pedir } from './cliente.js';

export async function solicitar(frase, { señal } = {}) {
  return pedir(RUTAS.supresion, { metodo: 'POST', cuerpo: { frase }, señal });
}

export async function consultar({ señal } = {}) {
  return pedir(RUTAS.supresion, { señal });
}

export async function cancelar({ señal } = {}) {
  return pedir(RUTAS.supresion, { metodo: 'DELETE', señal });
}

export async function retencion({ señal } = {}) {
  return pedir(RUTAS.retencion, { señal });
}
