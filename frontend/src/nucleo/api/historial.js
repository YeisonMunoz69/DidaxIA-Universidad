/**
 * `08-Contrato-del-Turno.md` §13 · El historial de conversaciones.
 *
 * Listar las propias y leer una. Exige sesión AUTENTICADA (§13.4) — no basta
 * la cookie anónima de `RP-02`: un sujeto anónimo tiene `sujeto == sesión`, y
 * su historial moriría al cerrar el navegador. Quien llama a este módulo
 * debe comprobar `sesion.autenticada` antes, no después.
 *
 * NO HAY `continuar(sesion)`. El contrato no lo ofrece — la conversación vive
 * en la sesión, en memoria del proceso (ver `Aplicacion.svelte`, comentario de
 * «Nueva conversación») — así que leer una sesión antigua es de solo lectura.
 * Volver a escribir es «Nueva conversación», que abre una sesión nueva.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md §13
 */
import { pedir, RUTAS } from './cliente.js';

/** Las conversaciones propias, agrupadas por sesión. `{ conversaciones: [...] }`. */
export async function listar({ señal } = {}) {
  return pedir(RUTAS.historial, { señal });
}

/** Un hilo completo. `{ sesion, mensajes: [...] }` — §13.2. */
export async function leer(sesion, { señal } = {}) {
  return pedir(`${RUTAS.historial}/${encodeURIComponent(sesion)}`, { señal });
}
