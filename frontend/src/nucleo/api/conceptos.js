/**
 * DD-13 · Banco de conceptos.
 *
 * Listar el banco, pedir la ficha de un concepto y sus relaciones.
 *
 * SE PIDE APARTE DEL TURNO. El turno solo dice QUE conceptos invocó, con su
 * identificador y su nombre; el contenido completo se pide cuando el estudiante
 * abre la ficha. Un turno que arrastrara tres conceptos enteros pesaría más que
 * la propia respuesta.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 * Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md
 */
import { RUTAS, pedir } from './cliente.js';

/** El banco entero, con identificador y nombre. Sin contenido. */
export async function listar({ señal } = {}) {
  return pedir(RUTAS.conceptos, { señal });
}

/** Un concepto con su explicación, sus relaciones y su simulación. */
export async function ficha(id, { señal } = {}) {
  return pedir(`${RUTAS.conceptos}/${encodeURIComponent(id)}`, { señal });
}
