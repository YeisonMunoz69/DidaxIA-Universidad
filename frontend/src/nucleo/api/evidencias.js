/**
 * La consola del investigador contra el backend · `EQ-021` / `EQ-023` · C2B.
 *
 * Cinco operaciones: listar, consultar el detalle, recuperar el PDF, aprobar y
 * rechazar con motivo. Nada más, y en particular **nada que guarde**.
 *
 * QUÉ NO HACE ESTE MÓDULO, Y ES LA MITAD DE SU RAZÓN DE SER
 * ----------------------------------------------------------
 * No escribe en `localStorage`, ni en `sessionStorage`, ni en IndexedDB, ni en
 * la dirección de navegación, ni en la consola. No cachea la cola, no memoriza
 * detalles y no conserva ningún documento entre llamadas.
 *
 * No es una precaución genérica: lo que circula por aquí son autorizaciones
 * firmadas por representantes legales de menores de edad. Un `localStorage` con
 * la cola dentro sobrevive al cierre de sesión, al cambio de persona en el
 * mismo equipo y a la revocación del rol — y el backend, que vuelve a autorizar
 * en cada petición, no tendría forma de enterarse.
 *
 * EL PDF SE DEVUELVE COMO `Blob`, NUNCA COMO DIRECCIÓN
 * ------------------------------------------------------
 * `archivo()` entrega los bytes. Quien los pinta construye su
 * `URL.createObjectURL()` **y lo revoca**: al cambiar de evidencia y al
 * desmontarse. Aquí no se crea ninguna porque este módulo no tiene ciclo de
 * vida en el que revocarla, y una Object URL que nadie revoca sigue viva
 * mientras dure la pestaña — con el documento entero en memoria y alcanzable
 * por cualquiera que sepa la dirección `blob:`.
 *
 * ⚠️ **La referencia opaca del almacenamiento privado no llega hasta aquí.** El
 * backend no la publica en ningún cuerpo ni cabecera; este módulo no la pide, no
 * la compone y no la conoce. Las direcciones se arman con el identificador de la
 * evidencia, que es un entero.
 *
 * LA CLASIFICACIÓN DE FALLOS NO SE APLANA
 * -----------------------------------------
 * Todo sale como `FalloDeRed` con su clase —`sin-sesion`, `sin-permiso`,
 * `peticion-invalida`, `mantenimiento`, `sin-red`…— y **ninguna se convierte en
 * una lista vacía**. Un 403 pintado como «no hay nada pendiente» le diría a una
 * investigadora que su cola está limpia cuando lo que pasa es que le retiraron
 * el rol; un 503 pintado igual le diría que no hay autorizaciones esperando
 * cuando puede haber una desde hace días. Los dos son mentiras que se pueden
 * actuar.
 *
 */
import { RUTAS, pedir, pedirArchivo } from './cliente.js';

/** Los cuatro filtros que el backend admite. Cerrado, como allá. */
export const FILTROS = Object.freeze(['pendiente', 'aprobada', 'rechazada', 'todos']);

/** El de por defecto, y el mismo que el servidor aplica sin decir nada. */
export const FILTRO_POR_DEFECTO = 'pendiente';

/**
 * Cuántas evidencias por página.
 *
 * El backend admite de 1 a 100 y no impone ninguna: veinte es lo que cabe en
 * una pantalla sin obligar a desplazarse hasta el final para saber si hay más.
 */
export const TAMANO_PAGINA = 20;

/**
 * El camino de una evidencia concreta.
 *
 * Se compone aquí y no en `RUTAS` porque lleva un identificador dentro; tener
 * las tres formas en un sitio evita que la del archivo y la del detalle
 * discrepen el día que el backend renombre la colección.
 */
function caminoDe(evidencia) {
  return `${RUTAS.evidencias}/${Number(evidencia)}`;
}

/**
 * La cola paginada.
 *
 * `cursor` se pasa **tal como lo devolvió el servidor** y nunca se compone: es
 * opaco a propósito, y un cliente que intentara construirlo estaría dependiendo
 * de una forma interna que el backend puede cambiar. Sin cursor, primera página.
 *
 * @param {{estado?: string, limite?: number, cursor?: string|null,
 *          señal?: AbortSignal}} opciones
 */
export async function listar({
  estado = FILTRO_POR_DEFECTO,
  limite = TAMANO_PAGINA,
  cursor = null,
  señal
} = {}) {
  const parametros = new URLSearchParams();
  if (estado) parametros.set('estado', estado);
  if (limite) parametros.set('limite', String(limite));
  // Sólo si lo hay: un `cursor=` vacío es una petición distinta de no mandarlo,
  // aunque el servidor los trate igual — y depender de esa equivalencia es
  // depender de una cortesía suya.
  if (cursor) parametros.set('cursor', cursor);

  const respuesta = await pedir(`${RUTAS.evidencias}?${parametros}`, { señal });
  return {
    evidencias: respuesta?.evidencias ?? [],
    cursorSiguiente: respuesta?.cursor_siguiente ?? null,
    hayMas: Boolean(respuesta?.hay_mas),
    filtro: respuesta?.filtro ?? estado,
    limite: respuesta?.limite ?? limite
  };
}

/**
 * El detalle de una evidencia. Es lo único que trae el motivo de un rechazo.
 *
 * Devuelve el documento tal cual, con sus claves del servidor: traducirlas aquí
 * añadiría un mapa que mantener y una forma más de que el cliente y el backend
 * discrepen sobre qué campos existen. Sólo se normaliza `motivo`, que llega
 * `null` cuando no corresponde.
 */
export async function detalle(evidencia, { señal } = {}) {
  const documento = await pedir(caminoDe(evidencia), { señal });
  return { ...documento, motivo: documento?.motivo ?? '' };
}

/**
 * El PDF, como `Blob`.
 *
 * Se pide **después** del detalle y no a la vez: si el archivo no se puede
 * recuperar —una reserva sin confirmar, el almacén caído— la pantalla todavía
 * tiene qué enseñar y qué explicar, en vez de quedarse en blanco.
 */
export async function archivo(evidencia, { señal } = {}) {
  return pedirArchivo(`${caminoDe(evidencia)}/archivo`, { señal });
}

/**
 * Aprueba una evidencia · `EQ-023`.
 *
 * La ruta es la que ya existía —singular, y con su contrato intacto—: C2A no la
 * movió y C2B no la duplica.
 */
export async function aprobar(evidencia, { señal } = {}) {
  return pedir(`${RUTAS.evidencia}/${Number(evidencia)}/revisar`, {
    metodo: 'POST',
    cuerpo: { resultado: 'aprobada' },
    señal
  });
}

/**
 * Rechaza una evidencia con su motivo · `EQ-021`.
 *
 * El motivo se recorta y **se exige aquí además de en la pantalla**: un rechazo
 * sin motivo deja a quien cargó el documento sin saber qué corregir, y la regla
 * no puede vivir sólo en un formulario que otro componente podría no usar. El
 * servidor lo exige por tercera vez, y la base por cuarta.
 */
export async function rechazar(evidencia, motivo, { señal } = {}) {
  const texto = String(motivo ?? '').trim();
  if (!texto) throw new Error('un rechazo exige un motivo comprensible');
  return pedir(`${RUTAS.evidencia}/${Number(evidencia)}/revisar`, {
    metodo: 'POST',
    cuerpo: { resultado: 'rechazada', motivo: texto },
    señal
  });
}
