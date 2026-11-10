/**
 * `EQ-013` · La biblioteca de fuentes.
 *
 * Listar obras, abrir la ficha de un fragmento y leer la transcripción de una
 * parte. Nada de esto se pide con una ruta: **sólo con identificadores
 * catalogados**, que es la barrera que el backend impone y este cliente
 * respeta por construcción — no hay ninguna función a la que se le pueda pasar
 * un nombre de archivo.
 *
 * SE PIDE APARTE DEL TURNO, igual que los conceptos de `DD-13`. El turno dice
 * QUÉ material recuperó —identificador, obra y un rótulo legible— y el texto se
 * pide cuando el estudiante lo abre. Un turno que arrastrara tres fragmentos
 * enteros pesaría más que la respuesta, y además los enviaría a quien no va a
 * leerlos, que es lo contrario de lo que la puerta de publicación busca.
 *
 * LOS ERRORES SON PARTE DEL CONTRATO
 * -----------------------------------
 * El backend responde con un `motivo` en clave estable —`obra_no_autorizada`,
 * `archivo_ausente`, `fragmento_inexistente`…— para que la pantalla elija su
 * estado **sin analizar el texto** del mensaje. Traducir el motivo a una
 * pantalla es del componente; conservarlo intacto es de aquí.
 *
 */
import { BASE, RUTAS, pedir } from './cliente.js';

/**
 * Forma de un identificador de fragmento. **La misma que el backend.**
 *
 * Se comprueba aquí además de allí para no gastar una petición en algo que se
 * sabe mal escrito, no para autorizar: la negativa efectiva la ejerce el
 * servidor, como todo en este árbol.
 */
const FRAGMENTO = /^F-\d{3}$/;

/** Forma de una clave de obra: tres mayúsculas. */
const CLAVE_DE_OBRA = /^[A-Z]{3}$/;

/** Forma del nombre de una parte dentro de su obra. */
const NOMBRE_DE_PARTE = /^[a-z0-9][a-z0-9-]{0,63}$/;

/** Si una cadena tiene forma de identificador de fragmento. */
export function esFragmento(id) {
  return typeof id === 'string' && FRAGMENTO.test(id);
}

/** Si una cadena tiene forma de clave de obra. */
export function esClaveDeObra(clave) {
  return typeof clave === 'string' && CLAVE_DE_OBRA.test(clave);
}

/** Si una cadena tiene forma de nombre de parte. */
export function esNombreDeParte(nombre) {
  return typeof nombre === 'string' && NOMBRE_DE_PARTE.test(nombre);
}

/** Todas las obras del catálogo, con su ficha y su disponibilidad. */
export async function obras({ señal } = {}) {
  return pedir(RUTAS.fuentesObras, { señal });
}

/** Índice de fragmentos del corpus; el texto se pide sólo al abrir uno. */
export async function fragmentos({ señal } = {}) {
  return pedir(RUTAS.fuentesFragmentos, { señal });
}

/** Una obra con sus partes catalogadas. */
export async function obra(clave, { señal } = {}) {
  return pedir(`${RUTAS.fuentesObras}/${encodeURIComponent(clave)}`, { señal });
}

/**
 * La ficha de un fragmento.
 *
 * ⚠️ **Puede venir sin `contenido`, y eso no es un fallo.** `FUENTES.md` separa
 * los metadatos bibliográficos —que se pueden mostrar siempre— del pasaje, que
 * necesita autorización de la obra. Cuando falta, el cuerpo trae
 * `motivo_sin_contenido` y la pantalla lo explica en vez de fingir un error.
 */
export async function fragmento(id, { señal } = {}) {
  return pedir(`${RUTAS.fuentesFragmentos}/${encodeURIComponent(id)}`, { señal });
}

/** La transcripción de una parte, ya en bloques tipados y sin HTML. */
export async function parte(clave, nombre, { señal } = {}) {
  const camino =
    `${RUTAS.fuentesObras}/${encodeURIComponent(clave)}` +
    `/partes/${encodeURIComponent(nombre)}`;
  return pedir(camino, { señal });
}

/**
 * La dirección del PDF dividido de una parte.
 *
 * ⚠️ **Devuelve una dirección, no el archivo.** El visor del navegador la pide
 * por su cuenta —con `Range`, si le hace falta— y el backend vuelve a comprobar
 * el permiso en esa petición. Descargar aquí el PDF para dárselo al visor
 * habría metido megabytes por el cliente sin ninguna ganancia.
 */
export function pdfDeParte(clave, nombre) {
  if (!esClaveDeObra(clave) || !esNombreDeParte(nombre)) return '';
  return (
    `${BASE}${RUTAS.fuentesObras}/${encodeURIComponent(clave)}` +
    `/partes/${encodeURIComponent(nombre)}/pdf`
  );
}

/** La dirección del PDF completo de una obra. */
export function pdfCompleto(clave) {
  if (!esClaveDeObra(clave)) return '';
  return `${BASE}${RUTAS.fuentesObras}/${encodeURIComponent(clave)}/pdf`;
}
