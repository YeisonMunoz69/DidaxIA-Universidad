/**
 * Consentimiento versionado, asentimiento y evidencia · `EQ-021` / `EQ-016`.
 *
 * Las cuatro escrituras del recorrido, más la consulta de versiones.
 *
 * ⚠️ UNA DECISIÓN, UNA PETICIÓN · `D1B`
 * ---------------------------------------------------------------
 * Aquí había `decidirTitular()` y `decidirAsentimiento()`, dos escrituras
 * separadas que el recorrido del menor llamaba una detrás de otra. Entre las
 * dos cabía —y ocurría— el estado que nadie decidió: el consentimiento del
 * titular registrado y el asentimiento no.
 *
 * `D0` §10.10 lo cierra con una acción y actos guardados **atómicamente por el
 * servidor**. `decidirConjunta()` es esa única llamada, y las dos rutas
 * parciales responden `410`. **No se conservan aquí**: no tienen consumidor, y
 * una función exportada es una invitación a volver a encadenarlas.
 *
 * Lo que este módulo NO hace, y es parte del contrato: no hay `Promise.all`, no
 * hay `Promise.allSettled` y no hay dos `fetch` para registrar una decisión.
 * Fingir atomicidad desde el navegador es exactamente la solución que `D0`
 * §10.10 descarta.
 *
 * ⚠️ LO QUE ESTE MÓDULO NO ENVÍA NUNCA, Y ES SU CONTRATO ENTERO
 * ---------------------------------------------------------------
 * **La versión.** Ni al otorgar, ni al rechazar, ni al revocar, ni al cargar la
 * evidencia. El servidor la resuelve con dos reglas que `EQ-022` separa:
 * otorgar y rechazar consumen la versión *requerida* —dejarla elegir al cliente
 * permitiría aceptar un texto ya desplazado— y revocar retira la concesión
 * *efectivamente otorgada*, aunque su documento haya vencido. Un cliente que
 * mandara un código de versión podría producir exactamente el fallo que el hito
 * A2 corrigió en el servidor.
 *
 * **El comprobante.** Lo calcula `comprobante_de()` en el servidor. Un recibo
 * que el navegador enviara probaría lo que el navegador quisiera; por eso el
 * recibo se *muestra*, no se construye —ver `recibo` en la respuesta—.
 *
 * ⚠️ NO HAY TEXTOS LEGALES TODAVÍA, Y ESO SE REPRESENTA
 * -------------------------------------------------------
 * `GET /api/consentimiento/versiones` devuelve hoy `null` en los tres alcances:
 * el equipo no ha aprobado ningún texto y el servidor no siembra ninguno.
 * `hayVersion()` existe para que la interfaz pueda impedir aceptar en vez de
 * inventar un documento. Registrar una decisión sin versión publicada responde
 * `409` con `estado: "sin_version"`, y ese caso se distingue de cualquier otro
 * conflicto por el cuerpo del error, no por el código.
 *
 */
import { RUTAS, pedir, pedirArchivo, pedirBinario } from './cliente.js';

/** El PDF es lo único que se acepta, y el límite lo fija `EQ-021`. */
export const TIPO_DE_EVIDENCIA = 'application/pdf';
export const TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024;

/** Las dos decisiones que una persona toma sobre un documento. Revocar NO es una. */
export const DECISIONES = Object.freeze(['otorgado', 'rechazado']);

/**
 * El DOCUMENTO exacto de una versión, por su código · `§8`.
 *
 * ⚠️ **Lo que esto corrige.** La pantalla afirma que «la huella identifica el
 * texto exacto que estás leyendo», y hasta la revisión R2 no era cierto: la
 * base guardaba la huella y no el documento, y lo único que se podía abrir eran
 * las páginas públicas del sitio —genéricas y editables—, que no son el
 * artefacto hasheado. Esto trae el artefacto.
 *
 * Se pide por CÓDIGO y nunca por ruta: el navegador no elige qué archivo se
 * abre, elige de qué versión quiere el texto. El servidor recalcula el SHA-256
 * antes de responder y devuelve `409` si no corresponde a la huella publicada,
 * así que un documento que no case con lo publicado **no llega a la pantalla**.
 */
export async function textoDeVersion(codigo, { señal } = {}) {
  return pedir(RUTAS.textoDeVersion(codigo), { señal });
}

/**
 * Qué documento rige ahora en cada alcance. Los tres pueden ser `null`.
 *
 * @returns {Promise<{titular: object|null, asentimiento: object|null,
 *                    representante: object|null}>}
 */
export async function versiones({ señal } = {}) {
  return pedir(RUTAS.versiones, { señal });
}

/**
 * ¿Hay una versión publicada de ese alcance?
 *
 * Una función y no un `!= null` suelto en cada pantalla: es la comprobación
 * que impide ofrecer «Autorizo» sobre un texto que no existe, y repetida en
 * cinco sitios acabaría faltando en el sexto.
 */
export function hayVersion(documento) {
  return Boolean(documento && documento.codigo);
}

/**
 * La única acción visible del recorrido · `D0` §10.10.
 *
 * Otorga o rechaza, y el servidor decide **cuántos actos** escribe: uno de
 * alcance `titular` para un adulto; ése y uno de `asentimiento` para un menor,
 * los dos en la misma transacción PostgreSQL.
 *
 * ⚠️ **Sólo viaja la decisión.** Ni edad, ni versión, ni alcance, ni huella, ni
 * comprobante: los cinco los resuelve el servidor con la fila de la persona
 * bloqueada, y mandar cualquiera de ellos es un `400`.
 *
 * @param {'otorgado'|'rechazado'} decision
 * @returns {Promise<object>} el estado recalculado con `recibos` —uno o dos—.
 */
export async function decidirConjunta(decision, { señal } = {}) {
  return pedir(RUTAS.decisionConjunta, {
    metodo: 'POST',
    cuerpo: { decision },
    señal
  });
}

/**
 * Revoca el consentimiento del titular · `EQ-022`.
 *
 * **No recibe nada**: ni versión, ni decisión, ni comprobante. Ruta propia y no
 * una decisión más de la de arriba porque las dos reglas de versión son
 * distintas, y compartir función las habría hecho compartir validación.
 *
 * No borra datos. Bloquea el tutor de inmediato, porque el acceso se calcula
 * sobre el estado persistido y el evento nuevo ya está ahí cuando responde.
 */
export async function revocarTitular({ señal } = {}) {
  return pedir(RUTAS.revocarTitular, { metodo: 'POST', señal });
}

/**
 * El menor retira su propio asentimiento, sin tocar el del titular.
 *
 * ⚠️ Su decisión inicial ya **no** tiene función aquí: la registra
 * `decidirConjunta()` junto con la del titular. Retirarla sí sigue siendo un
 * acto suyo y de una sola dimensión (`EQ-016`), y por eso conserva su ruta.
 */
export async function revocarAsentimiento({ señal } = {}) {
  return pedir(RUTAS.revocarAsentimiento, { metodo: 'POST', señal });
}

/**
 * Lo que el cliente puede comprobar del archivo ANTES de subirlo, o `''`.
 *
 * Las tres comprobaciones son las mismas que hace el servidor, y por eso el
 * texto se parece: aquí sirven para no hacer subir diez megas que van a ser
 * rechazados, no para autorizar nada. **El backend sigue siendo la autoridad**
 * —valida además la estructura del PDF con `pypdf`, que esto no puede hacer—.
 */
export function motivoParaNoSubir(archivo) {
  if (!archivo) return 'Elige el archivo con la autorización firmada.';
  if (archivo.type !== TIPO_DE_EVIDENCIA) {
    return 'La autorización se recibe en PDF. Ese archivo tiene otro formato.';
  }
  if (!archivo.size) return 'Ese archivo está vacío.';
  if (archivo.size > TAMANO_MAXIMO_BYTES) {
    return 'La autorización no puede pasar de 10 MB.';
  }
  return '';
}

/**
 * Descarga la plantilla aprobada con la fecha que estampó el servidor.
 *
 * Se recibe como `Blob` autenticado: la ruta comprueba que sea un estudiante
 * menor, que no tenga una supresión en curso y que exista una versión vigente.
 * El URL temporal se revoca en el mismo turno; el formulario sin firmar no se
 * conserva en ningún almacén del navegador.
 */
export async function descargarFormatoRepresentante({ señal } = {}) {
  const documento = await pedirArchivo(RUTAS.formatoRepresentante, { señal });
  const direccion = URL.createObjectURL(documento);
  try {
    const enlace = document.createElement('a');
    enlace.href = direccion;
    enlace.download = 'autorizacion-representante-menor.pdf';
    enlace.hidden = true;
    document.body.append(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(direccion);
  }
}

/**
 * Sube la autorización firmada del representante como cuerpo binario.
 *
 * El `File` del `<input type="file">` es un `Blob` y se manda tal cual: el
 * navegador lo transmite sin copiarlo entero a memoria.
 *
 * ⚠️ **El archivo no se guarda en ningún almacén del navegador**, ni él ni su
 * hash. Es un documento firmado con datos de un tercero —el representante— y
 * `localStorage` lo dejaría legible por cualquier guion de la página.
 */
export async function cargarEvidencia(archivo, { señal } = {}) {
  return pedirBinario(RUTAS.evidencia, {
    contenido: archivo,
    tipo: TIPO_DE_EVIDENCIA,
    // Un PDF de hasta 10 MB sobre datos móviles puede tardar más que un
    // turno de chat. Mantener el límite, pero no cortar la carga a los 30 s.
    espera: 90_000,
    señal
  });
}
