/**
 * Consulta y exportación de datos personales.
 *
 * Da servicio al panel de datos personales. RP-19 y RU-06.
 *
 * DOS OPERACIONES Y NO UNA, Y LA LEY LAS DISTINGUE
 * --------------------------------------------------
 * Mirar y llevarse una copia son dos derechos distintos de la Ley 1581, y el
 * backend los separa en dos rutas. Fundir «exportar» en «consultar» —devolver
 * lo mismo y que el cliente arme el archivo— haría que el registro no pudiera
 * distinguir quién solo miró de quién se llevó sus datos.
 *
 * ⚠️ EL TERCER DERECHO YA NO SE EJERCE DESDE AQUÍ
 * ------------------------------------------------
 * La supresión dejó de ser una operación de este módulo: es un trámite
 * reversible con reautenticación, frase y 24 horas para cancelar, y vive en
 * `api/gobierno.js`. Ver la nota al pie sobre la función retirada.
 *
 */
import { pedir, pedirArchivo, pedirBinario } from './cliente.js';

const RUTA = '/datos-personales';

/**
 * Lo que el sistema tiene sobre esta sesión, tal cual lo tiene.
 *
 * `via_de_supresion` señala hoy `/api/datos/supresion`; hasta el hito R2
 * anunciaba `DELETE /api/datos-personales/por-identidad`, que ya no existe —era
 * la respuesta con la que alguien consulta qué se guarda de él, y mandaba a una
 * puerta cerrada a quien intentara ejercer su derecho—.
 *
 * @returns {Promise<{sesion: string, rol: string, consentimiento: string,
 *                    via_de_supresion: {disponible: boolean, ruta: string|null,
 *                                       motivo: string}}>}
 */
export async function consultar({ señal } = {}) {
  return pedir(RUTA, { señal });
}

/** Lo mismo, empaquetado con su fecha para llevárselo. */
export async function exportar({ señal } = {}) {
  return pedir(`${RUTA}/exportar`, { señal });
}

/** Foto privada de la cuenta como URL temporal del navegador, o `null`. */
export async function consultarFoto({ señal } = {}) {
  try {
    const archivo = await pedirArchivo(`${RUTA}/foto`, { tipo: 'image/webp', señal });
    return URL.createObjectURL(archivo);
  } catch (error) {
    if (error?.estado === 404) return null;
    throw error;
  }
}

/** Recodifica en el servidor y sustituye la foto vigente. */
export async function guardarFoto(archivo, { señal } = {}) {
  return pedirBinario(`${RUTA}/foto`, {
    contenido: archivo,
    tipo: archivo?.type || 'application/octet-stream',
    metodo: 'PUT',
    señal
  });
}

/** Retira la referencia y los bytes de la foto actual. */
export async function retirarFoto({ señal } = {}) {
  return pedir(`${RUTA}/foto`, { metodo: 'DELETE', señal });
}

/*
 * ⚠️ `suprimir()` SE RETIRÓ EN C1. NO HAY AQUÍ NINGÚN `DELETE`.
 *
 * Llamaba a `DELETE /api/datos-personales`, que borraba perfil, registro de
 * turnos, historial y matrícula **al recibir la petición** y además cerraba la
 * sesión. `EQ-022` sustituyó ese contrato: la supresión exige reautenticación
 * reciente acreditada por el servidor, frase de confirmación, aviso al correo
 * institucional y 24 horas para cancelar. Un `DELETE` inmediato no tiene
 * ninguna de las cuatro cosas, y la auditoría V-B lo listó el primero de sus
 * nueve invariantes porque era la vía por la que el trámite entero se saltaba.
 *
 * La ruta responde **410** desde el hito R2. No se deja una función que la
 * llame: enseñar el 410 no sería compatibilidad, y fingir éxito lo sería menos.
 * El trámite vive en `api/gobierno.js`.
 */

/**
 * Deja la exportación en un archivo del equipo del estudiante.
 *
 * Vive aquí y no en el componente porque es el final de `exportar()`: llevarse
 * una copia no termina cuando el servidor responde, termina cuando el archivo
 * está en su disco. Se usa un `Blob` y no un enlace al servidor para que la
 * descarga no vuelva a pedir el dato por una URL — §Privacidad: un dato
 * personal no viaja en una dirección que el navegador guarda en su historial.
 */
export function descargar(exportacion, nombre = 'mis-datos.json') {
  const blob = new Blob([JSON.stringify(exportacion, null, 2)], {
    type: 'application/json'
  });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}
