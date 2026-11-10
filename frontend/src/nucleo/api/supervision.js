/**
 * Cola de revisión del docente.
 *
 * Listar pendientes, aprobar, editar y rechazar. RU-12.
 *
 * POR MUESTREO Y POR EXCEPCIÓN, Y ESO SE NOTA EN LA INTERFAZ DE ESTE MÓDULO
 * -------------------------------------------------------------------------
 * `listar()` admite filtros y un tope, y **no** existe un «aprobar todo».
 * Con treinta o sesenta estudiantes, revisar cada respuesta es insostenible y
 * el sistema no lo pide; pero un botón que aprueba en bloque convierte la
 * revisión en un trámite y deja de ser revisión. La ausencia es deliberada.
 *
 * `editar()` MANDA EL TEXTO CORREGIDO, y por eso está separado de `aprobar()`.
 * Un docente que corrige antes de aprobar está haciendo algo distinto de
 * aprobar, y el registro tiene que poder distinguirlos: `RP-17` pide poder
 * reconstruir qué se emitió y quién lo decidió.
 *
 */
import { BASE, pedir } from './cliente.js';

const RUTA = '/supervision';

/**
 * Lo pendiente de revisión.
 *
 * `tope`/`desde` paginan sobre el mismo orden (`recibido`, el más antiguo
 * primero): `desde` es cuántos se saltan, `tope` cuántos se piden después de
 * saltar — juntos son una página. `ColaDeSupervision.svelte` los usa así,
 * en vez de acumular con un tope creciente («cargar más»), desde 2026-08-22.
 *
 * @param {{urgencia?: string, clase?: string, tipo?: string, tope?: number, desde?: number}} filtros
 */
export async function listar(filtros = {}, { señal } = {}) {
  const q = new URLSearchParams(
    Object.entries(filtros).filter(([, v]) => v !== '' && v != null)
  ).toString();
  return pedir(RUTA + (q ? `?${q}` : ''), { señal });
}

/** Aprueba tal cual. */
export async function aprobar(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/aprobar`, { metodo: 'POST', señal });
}

/** Aprueba con el texto corregido por el docente. Distinto de aprobar. */
export async function editar(id, texto, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/editar`, {
    metodo: 'POST', cuerpo: { texto }, señal
  });
}

/** Rechaza la propuesta y publica la corrección del docente en el hilo. */
export async function rechazar(id, texto, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/rechazar`, {
    metodo: 'POST', cuerpo: { texto }, señal
  });
}

/** Aclaraciones que un docente añadió a una conversación propia del estudiante. */
export async function misAclaraciones(sesion, { señal } = {}) {
  const q = new URLSearchParams({ sesion }).toString();
  return pedir(`${RUTA}/mis-aclaraciones?${q}`, { señal });
}

/** El prefijo, para que quien lea sepa contra qué se está pidiendo. */
export const PREFIJO = BASE + RUTA;
