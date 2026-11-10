import { normalizarColores } from './colores.js';

const CLAVE='didaxia.aplicacion.apariencia.v1';
function normalizar(datos) {
  return {...normalizarColores(datos),tema:['claro','oscuro','sistema'].includes(datos?.tema) ? datos.tema : 'sistema'};
}
export function leerAparienciaLocal() {
  try {
    const guardada=globalThis.localStorage?.getItem(CLAVE);
    return guardada ? normalizar(JSON.parse(guardada)) : null;
  } catch { return null; }
}
export function recordarAparienciaLocal(datos) {
  try { globalThis.localStorage?.setItem(CLAVE,JSON.stringify(normalizar(datos))); }
  catch {  }
}
