/**
 * Supresión reversible y retención · `EQ-022`.
 *
 * El trámite del derecho de supresión, que **no es un borrado**. Tres rutas
 * sobre el mismo recurso: abrirlo, consultarlo y cancelarlo.
 *
 * ⚠️ POR QUÉ NO HAY AQUÍ NINGUNA FUNCIÓN QUE BORRE
 * --------------------------------------------------
 * `DELETE /api/datos-personales` y `DELETE /api/datos-personales/por-identidad`
 * ejecutaban la cascada al recibir la petición: sin reautenticación, sin frase,
 * sin aviso y sin las 24 horas para cancelar. Responden **410** desde el hito
 * R2 y la auditoría V-B las puso como el primero de sus nueve invariantes,
 * porque eran la vía por la que todo el trámite se podía saltar.
 *
 * La función que las llamaba —`datos-personales.js::suprimir()`— se retiró en
 * C1. No se sustituye por un alias ni por una capa de compatibilidad: llamar a
 * una ruta que responde 410 y enseñar el error no es compatibilidad, y enseñar
 * un éxito lo sería todavía menos.
 *
 * ⚠️ `reautenticada_en` NO SE ENVÍA, Y NO EXISTE EN ESTE ARCHIVO
 * ---------------------------------------------------------------
 * La prueba de reautenticación la construye y la guarda el servidor cuando
 * `POST /api/sesion/reautenticar` verifica un `id_token` recién firmado por
 * Google para ESTA cuenta. Una marca de tiempo enviada por el cliente no
 * demuestra nada: cualquiera que llame al API escribe la fecha que quiera. Por
 * eso `solicitar()` manda **sólo la frase**, y un trámite sin prueba vigente
 * vuelve con `401` y `estado: "reautenticacion_requerida"`.
 *
 * La frase exacta la exige y la comprueba el backend. Este módulo no la
 * declara ni la valida: hacerlo aquí crearía una segunda definición que puede
 * discrepar de la única que decide.
 *
 */
import { RUTAS, pedir } from './cliente.js';

/**
 * Abre el trámite. **No borra nada.**
 *
 * Devuelve el estado, cuándo se solicitó, hasta cuándo se puede cancelar, el
 * plazo de resolución y si el aviso por correo salió —`aviso_enviado`, que se
 * representa y no se finge: `EQ-024` dice que el canal no decide el trámite—.
 *
 * @param {string} frase la que el titular escribió, tal cual
 */
export async function solicitar(frase, { señal } = {}) {
  return pedir(RUTAS.supresion, { metodo: 'POST', cuerpo: { frase }, señal });
}

/** El trámite abierto —o `null`— y el historial de los ya cerrados. */
export async function consultar({ señal } = {}) {
  return pedir(RUTAS.supresion, { señal });
}

/**
 * Cancela el trámite dentro de las 24 horas · `EQ-022`.
 *
 * Pasado el plazo, el servidor responde `409` con el motivo: que la ventana se
 * cierre **no ejecuta nada**, sólo retira la cancelación por parte del titular.
 */
export async function cancelar({ señal } = {}) {
  return pedir(RUTAS.supresion, { metodo: 'DELETE', señal });
}

/**
 * La política de retención vigente.
 *
 * Hoy `sustentacion_en` y `limite` son `null` porque la fecha todavía no
 * existe. Se enseña esa ausencia; una fecha inventada sería peor que ninguna.
 */
export async function retencion({ señal } = {}) {
  return pedir(RUTAS.retencion, { señal });
}
