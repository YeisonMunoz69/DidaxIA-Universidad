/** Cliente del catálogo KPI v1.1. Ningún filtro se omite silenciosamente. */
import { pedir } from './cliente.js';

function consulta(parametros = {}) {
  const salida = new URLSearchParams();
  for (const [nombre, valor] of Object.entries(parametros)) {
    if (valor !== null && valor !== undefined && String(valor).trim() !== '') {
      salida.set(nombre, String(valor).trim());
    }
  }
  return salida.size ? `?${salida}` : '';
}

export function catalogoDocente({ señal } = {}) {
  return pedir('/kpi/catalogo', { señal });
}

export function catalogoInstitucional({ señal } = {}) {
  return pedir('/investigacion/kpi/catalogo', { señal });
}

export function indicadoresDocente(clase, parametros = {}, { señal } = {}) {
  return pedir(`/kpi${consulta({ ...parametros, clase })}`, { señal });
}

export function indicadoresInstitucional(parametros = {}, { señal } = {}) {
  return pedir(`/investigacion/kpi${consulta(parametros)}`, { señal });
}
