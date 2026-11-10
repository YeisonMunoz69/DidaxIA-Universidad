/** Informes KPI binarios; los bytes no se guardan en localStorage. */
import { pedirArchivo } from './cliente.js';

export function vistaPrevia(cuerpo, { señal } = {}) {
  return pedirArchivo('/investigacion/informes/vista-previa', {
    metodo: 'POST', cuerpo, señal
  });
}

export function descargar(cuerpo, { señal } = {}) {
  return pedirArchivo('/investigacion/informes/descargar', {
    metodo: 'POST', cuerpo, señal
  });
}
