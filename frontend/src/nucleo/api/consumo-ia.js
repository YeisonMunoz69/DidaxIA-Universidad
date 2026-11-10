/** Consumo financiero-operativo, reservado al investigador. */
import { pedir, pedirArchivo } from './cliente.js';

function consulta({ desde, hasta, secciones }) {
  const parametros = new URLSearchParams({ desde, hasta });
  if (secciones) parametros.set('secciones', secciones.join(','));
  return parametros.toString();
}

export function resumen(filtros, { señal } = {}) {
  return pedir(`/investigacion/consumo-ia?${consulta(filtros)}`, { señal });
}

export function exportarCSV(filtros, { señal } = {}) {
  return pedirArchivo(`/investigacion/consumo-ia/exportar.csv?${consulta(filtros)}`, {
    tipo: 'text/csv', señal
  });
}

export function exportarPDF(filtros, { señal } = {}) {
  return pedirArchivo(`/investigacion/consumo-ia/exportar.pdf?${consulta(filtros)}`, { señal });
}
