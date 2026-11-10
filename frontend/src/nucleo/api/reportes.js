import { pedir, pedirArchivo } from './cliente.js';

export function crear(cuerpo, { señal } = {}) {
  return pedir('/reportes', { metodo: 'POST', cuerpo, señal, espera: 35_000 });
}

export function mios({ señal } = {}) {
  return pedir('/reportes/mios', { señal });
}

export function institucionales(estado = '', { señal } = {}) {
  const consulta = estado ? `?estado=${encodeURIComponent(estado)}` : '';
  return pedir(`/investigacion/reportes${consulta}`, { señal });
}

export function actualizar(id, cuerpo, { señal } = {}) {
  return pedir(`/investigacion/reportes/${Number(id)}`, {
    metodo: 'PATCH', cuerpo, señal
  });
}

export function captura(id, { propia = false, señal } = {}) {
  const ruta = propia
    ? `/reportes/mios/${Number(id)}/captura`
    : `/investigacion/reportes/${Number(id)}/captura`;
  return pedirArchivo(ruta, { tipo: 'image/webp', señal });
}
