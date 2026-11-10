import { pedir } from './cliente.js';

const base = '/investigacion/conversaciones';
function consulta(filtros) {
  const parametros = new URLSearchParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    if (valor !== '' && valor !== null && valor !== undefined) parametros.set(clave, String(valor));
  }
  return `?${parametros}`;
}
export const estudiantes = (filtros, señal) => pedir(`${base}/estudiantes${consulta(filtros)}`, { señal });
export const conversaciones = (sujeto, filtros, señal) =>
  pedir(`${base}/${encodeURIComponent(sujeto)}${consulta(filtros)}`, { señal });
export const hilo = (sujeto, sesion, filtros, señal) =>
  pedir(`${base}/${encodeURIComponent(sujeto)}/${encodeURIComponent(sesion)}${consulta(filtros)}`, { señal });
