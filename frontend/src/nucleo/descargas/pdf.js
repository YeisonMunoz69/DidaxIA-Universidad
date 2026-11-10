/** Descarga un PDF temporal sin conservar bytes ni object URLs en el navegador. */

import { descargarBlob } from './archivo.js';

const ESPERA_REVOCACION_MS = 60_000;

export function nombrePDFSeguro(nombre) {
  const base = String(nombre || 'didaxia-documento.pdf')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\.pdf$/i, '')
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/^[._-]+|[._-]+$/g, '')
    .slice(0, 180);
  return `${base || 'didaxia-documento'}.pdf`;
}

export function descargarPDF(blob, nombre, {
  documento = document,
  urls = URL,
  esperaRevocacion = ESPERA_REVOCACION_MS
} = {}) {
  if (!blob || typeof blob.size !== 'number' || blob.size <= 0) {
    throw new TypeError('El informe PDF está vacío.');
  }
  if (String(blob.type || '').toLowerCase() !== 'application/pdf') {
    throw new TypeError('La respuesta recibida no es un PDF.');
  }

  return descargarBlob(blob, nombrePDFSeguro(nombre), {documento,urls,esperaRevocacion});
}
