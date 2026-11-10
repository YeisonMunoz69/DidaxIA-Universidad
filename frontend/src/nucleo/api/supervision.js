import { BASE, pedir } from './cliente.js';

const RUTA = '/supervision';

export async function listar(filtros = {}, { señal } = {}) {
  const q = new URLSearchParams(
    Object.entries(filtros).filter(([, v]) => v !== '' && v != null)
  ).toString();
  return pedir(RUTA + (q ? `?${q}` : ''), { señal });
}

export async function aprobar(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/aprobar`, { metodo: 'POST', señal });
}

export async function editar(id, texto, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/editar`, {
    metodo: 'POST', cuerpo: { texto }, señal
  });
}

export async function rechazar(id, texto, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/rechazar`, {
    metodo: 'POST', cuerpo: { texto }, señal
  });
}

export async function misAclaraciones(sesion, { señal } = {}) {
  const q = new URLSearchParams({ sesion }).toString();
  return pedir(`${RUTA}/mis-aclaraciones?${q}`, { señal });
}

export const PREFIJO = BASE + RUTA;
