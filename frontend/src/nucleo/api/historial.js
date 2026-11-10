import { pedir, RUTAS } from './cliente.js';

export async function listar({ señal } = {}) {
  return pedir(RUTAS.historial, { señal });
}

export async function leer(sesion, { señal } = {}) {
  return pedir(`${RUTAS.historial}/${encodeURIComponent(sesion)}`, { señal });
}
