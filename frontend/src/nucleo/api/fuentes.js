import { BASE, RUTAS, pedir } from './cliente.js';

const FRAGMENTO = /^F-\d{3}$/;

const CLAVE_DE_OBRA = /^[A-Z]{3}$/;

const NOMBRE_DE_PARTE = /^[a-z0-9][a-z0-9-]{0,63}$/;

export function esFragmento(id) {
  return typeof id === 'string' && FRAGMENTO.test(id);
}

export function esClaveDeObra(clave) {
  return typeof clave === 'string' && CLAVE_DE_OBRA.test(clave);
}

export function esNombreDeParte(nombre) {
  return typeof nombre === 'string' && NOMBRE_DE_PARTE.test(nombre);
}

export async function obras({ señal } = {}) {
  return pedir(RUTAS.fuentesObras, { señal });
}

export async function fragmentos({ señal } = {}) {
  return pedir(RUTAS.fuentesFragmentos, { señal });
}

export async function obra(clave, { señal } = {}) {
  return pedir(`${RUTAS.fuentesObras}/${encodeURIComponent(clave)}`, { señal });
}

export async function fragmento(id, { señal } = {}) {
  return pedir(`${RUTAS.fuentesFragmentos}/${encodeURIComponent(id)}`, { señal });
}

export async function parte(clave, nombre, { señal } = {}) {
  const camino =
    `${RUTAS.fuentesObras}/${encodeURIComponent(clave)}` +
    `/partes/${encodeURIComponent(nombre)}`;
  return pedir(camino, { señal });
}

export function pdfDeParte(clave, nombre) {
  if (!esClaveDeObra(clave) || !esNombreDeParte(nombre)) return '';
  return (
    `${BASE}${RUTAS.fuentesObras}/${encodeURIComponent(clave)}` +
    `/partes/${encodeURIComponent(nombre)}/pdf`
  );
}

export function pdfCompleto(clave) {
  if (!esClaveDeObra(clave)) return '';
  return `${BASE}${RUTAS.fuentesObras}/${encodeURIComponent(clave)}/pdf`;
}
