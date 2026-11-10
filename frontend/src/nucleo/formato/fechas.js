/**
 * Formato de fechas y duraciones en español.
 *
 * El archivo existía **vacío** desde el primer día: sólo esta cabecera. Mientras
 * tanto, tres pantallas del recorrido del estudiante escribieron cada una su
 * propia línea con la misma llamada —`toLocaleString('es-CO', { dateStyle:
 * 'long', timeStyle: 'short' })`— y su propio `try/catch`.
 *
 * C2B necesitaba la cuarta. Se escribe aquí, que es donde el proyecto ya había
 * decidido que vive, en vez de dejar una cuarta copia suelta.
 *
 *
 * POR QUÉ SE ATRAPA EL FALLO EN VEZ DE DEJARLO SUBIR
 * ----------------------------------------------------
 * Una fecha que el servidor mande mal —o que no mande— no puede tumbar la
 * pantalla que la enseña. Lo que se pierde es una línea de texto; lo que se
 * ganaría propagando es un componente en blanco donde había una cola de
 * revisión. Se devuelve una marca visible y no una cadena vacía: un hueco se lee
 * como «esto no tiene fecha», que sería falso.
 *
 */

/** Lo que se enseña cuando la fecha no se puede interpretar. */
export const FECHA_ILEGIBLE = 'fecha no disponible';

/**
 * Una marca ISO del servidor, en español y con hora.
 *
 * `es-CO` explícito y no la configuración del navegador: el sistema es de una
 * institución colombiana y una misma pantalla compartida no debería cambiar de
 * formato según quién la abra.
 *
 * @param {string|Date|null|undefined} valor
 * @returns {string}
 */
export function fechaLegible(valor) {
  if (!valor) return FECHA_ILEGIBLE;
  try {
    const fecha = valor instanceof Date ? valor : new Date(valor);
    if (Number.isNaN(fecha.getTime())) return FECHA_ILEGIBLE;
    return fecha.toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
  } catch {
    return FECHA_ILEGIBLE;
  }
}
