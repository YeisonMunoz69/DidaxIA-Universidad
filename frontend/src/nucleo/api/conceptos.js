import { RUTAS, pedir } from './cliente.js';

export async function listar({ señal } = {}) {
  return pedir(RUTAS.conceptos, { señal });
}

export async function ficha(id, { señal } = {}) {
  return pedir(`${RUTAS.conceptos}/${encodeURIComponent(id)}`, { señal });
}
