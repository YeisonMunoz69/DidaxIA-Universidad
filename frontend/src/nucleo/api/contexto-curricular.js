import { pedir } from './cliente.js';

const RUTA = '/contexto-curricular';

export async function leer(clase, { señal } = {}) {
  return pedir(`${RUTA}?clase=${encodeURIComponent(clase)}`, { señal });
}

export async function guardar(contexto, { señal } = {}) {
  return pedir(RUTA, { metodo: 'PUT', cuerpo: contexto, señal });
}
