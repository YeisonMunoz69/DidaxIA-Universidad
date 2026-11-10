/**
 * Contexto del curso.
 *
 * Lectura y escritura del contexto que configura el docente.
 *
 * ES CONFIGURACIÓN DEL CURSO, NO DEL ESTUDIANTE. Qué unidad se está viendo, con
 * qué notación y con qué material. Nada de lo que se escribe aquí describe a
 * nadie: describe la asignatura. Es la razón de que este módulo no tenga nada
 * que ver con `RP-19` ni con el consentimiento.
 *
 */
import { pedir } from './cliente.js';

const RUTA = '/contexto-curricular';

/** El contexto vigente. */
export async function leer(clase, { señal } = {}) {
  return pedir(`${RUTA}?clase=${encodeURIComponent(clase)}`, { señal });
}

/** Lo guarda. El servidor valida; aquí solo se transporta. */
export async function guardar(contexto, { señal } = {}) {
  return pedir(RUTA, { metodo: 'PUT', cuerpo: contexto, señal });
}
