/**
 * Clasificación del fallo y qué se dice.
 *
 * Distingue sin red, servidor caído, mantenimiento (`EQ-024`), turno
 * interrumpido, falta de sesión y los rechazos con los que el backend de la
 * Fase 3 niega una operación concreta.
 * Implementa RP-17: nunca se muestra contenido matemático sin sello. Si el
 * turno se interrumpió a mitad, la última fase emitida dice dónde se quedó,
 * y eso sí se muestra: es la primera vez que la degradación puede ser
 * específica.
 *
 * POR QUÉ LA CLASIFICACIÓN VIVE AQUÍ Y NO EN `cliente.js`
 * --------------------------------------------------------
 * `cliente.js` sabe de HTTP; este archivo sabe de qué se le dice a una
 * persona. Mezclarlos haría que añadir un código de estado obligara a tocar
 * el texto que lee el estudiante, y al revés. Además `RP-17` exige que la
 * degradación esté en un solo sitio, y ese sitio es éste: `cliente.js` la
 * produce, `degradacion.js` la interpreta.
 *
 * LA REGLA QUE NO SE RELAJA · `RP-17` Y CONTRATO §8.3
 * ----------------------------------------------------
 * Una respuesta degradada NO LLEVA BLOQUES. Si el fallo impidió verificar, el
 * resultado no viaja: emitirlo sin sello sería exactamente lo que `RP-01`
 * prohíbe, y hacerlo con sello sería mentir. `sanear()` lo garantiza aunque el
 * servidor se equivoque y los mande — que un backend futuro cometa ese error
 * es más probable que no, y es barato defenderse aquí.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 */
import { mensajeDe } from './mensajes.js';

/** Sólo los fallos técnicos usan el océano; un rechazo no es una desconexión. */
export function modoDeContingencia(respuesta) {
  if (respuesta?.situacion !== 'degradado') return null;
  if (respuesta.clase === 'sin-red') return 'offline';
  if (!respuesta.clase || ['tiempo-agotado', 'servidor-caido', 'turno-interrumpido',
    'mantenimiento', 'desconocido'].includes(respuesta.clase)) return 'error_respuesta';
  return null;
}

/**
 * Las clases de fallo. Cerrada: una nueva se añade aquí y en `mensajes.js`.
 *
 * ⚠️ **`sesion-vencida` se partió en tres en C1.** Era la única clase para
 * 401 y 403, y con ella el frontend no podía distinguir las tres cosas que el
 * backend de la Fase 3 dice con esos códigos: «no hay sesión» —el estado
 * normal de quien acaba de llegar, `EQ-020`—, «esta ruta no es de su rol» y
 * «hace falta reautenticarse ahora mismo». Las tres se resolvían enseñando
 * «Tu sesión caducó», que en el primer caso es directamente falso.
 *
 * `mantenimiento` es la otra separación y es la que `EQ-024` exige: un 503 no
 * es «el servidor se rompió», es «la base no está lista y no se puede afirmar
 * nada». Pintarlo como caída invitaba a reintentar sin decir qué esperar; y
 * peor, mezclado con `servidor-caido` se podía acabar tratando como lista
 * vacía o formulario en blanco.
 */
export const CLASES = Object.freeze([
  'sin-red',
  'servidor-caido',
  'mantenimiento',
  'tiempo-agotado',
  'sin-sesion',
  'sin-permiso',
  'peticion-invalida',
  'conflicto',
  'retirada',
  'archivo-rechazado',
  'turno-interrumpido',
  'desconocido'
]);

/**
 * El error que `cliente.js` levanta. Nunca sale de la red un error crudo.
 *
 * Lleva `clase` porque quien lo recibe tiene que decidir sin volver a mirar
 * códigos de estado, y `estado` porque a veces hace falta para depurar — pero
 * el estado NO se le enseña al estudiante: eso lo decide `describir()`.
 */
export class FalloDeRed extends Error {
  constructor(clase, { estado = 0, causa = null, cuerpo = null } = {}) {
    super(`fallo de red (${clase})`);
    this.name = 'FalloDeRed';
    this.clase = CLASES.includes(clase) ? clase : 'desconocido';
    this.estado = estado;
    this.causa = causa;
    /**
     * El cuerpo JSON que acompañó al rechazo, cuando lo hubo.
     *
     * ⚠️ **Sin esto, C1 no podía cumplir su contrato.** El backend distingue
     * en el cuerpo casos que el código de estado funde: un 409 puede ser
     * `sin_version` —no hay texto legal publicado, y hay que impedir aceptar—
     * o una transición inválida; un 401 puede ser `sin_sesion` o
     * `reautenticacion_requerida`. Deducirlos del número era imposible, y
     * adivinarlos habría sido inventar autorización.
     *
     * Es lo que el servidor dijo, no lo que el cliente supone: `estadoDe()` lo
     * lee y nadie lo escribe.
     */
    this.cuerpo = cuerpo;
  }

  /** El `estado` que el backend nombró en el cuerpo, o `''`. Nunca lo inventa. */
  get estadoDelServidor() {
    const valor = this.cuerpo?.estado;
    return typeof valor === 'string' ? valor : '';
  }

  /** El `detalle` redactado por el backend, o `''`. */
  get detalle() {
    const valor = this.cuerpo?.detalle;
    return typeof valor === 'string' ? valor : '';
  }
}

/**
 * Clasifica un fallo de transporte por su código de estado.
 *
 * `0` es la marca de que la petición no llegó a salir o no volvió: el
 * navegador no distingue «sin wifi» de «servidor inalcanzable», y fingir que
 * sí sería inventar. Se trata como sin red, que es lo que el estudiante puede
 * comprobar por sí mismo.
 */
export function clasificarEstado(estado) {
  if (!estado) return 'sin-red';
  // 401 es el estado NORMAL de quien todavía no ha entrado (`EQ-020`), no una
  // avería. Quien lo reciba manda a la entrada institucional; no pinta una
  // caída del sistema ni un formulario en blanco.
  if (estado === 401) return 'sin-sesion';
  if (estado === 403) return 'sin-permiso';
  if (estado === 400) return 'peticion-invalida';
  if (estado === 409) return 'conflicto';
  if (estado === 410) return 'retirada';
  if (estado === 413 || estado === 415) return 'archivo-rechazado';
  if (estado === 408 || estado === 504) return 'tiempo-agotado';
  // `EQ-024` · el 503 de `rutas/comun.py::mantenimiento()`. Va ANTES del
  // rango 5xx genérico porque es el único que tiene una salida concreta que
  // ofrecer —esperar y reintentar— y porque no puede acabar representado como
  // éxito, lista vacía ni consentimiento pendiente.
  if (estado === 503) return 'mantenimiento';
  if (estado >= 500) return 'servidor-caido';
  return 'desconocido';
}

/**
 * Convierte lo que sea que se atrapó en una clase conocida.
 *
 * `AbortError` es el nombre que el navegador da tanto al tiempo agotado como
 * a una cancelación deliberada. `cliente.js` distingue las dos poniendo su
 * propio motivo en el `AbortController`, y aquí se lee ese motivo: sin él,
 * cancelar un turno para escribir otro se le anunciaría al estudiante como
 * un fallo del sistema.
 */
export function clasificar(error) {
  if (error instanceof FalloDeRed) return error.clase;
  if (error?.name === 'AbortError') {
    return error?.motivo === 'tiempo' ? 'tiempo-agotado' : 'desconocido';
  }
  if (error?.name === 'TypeError') return 'sin-red';   // fetch no llegó a salir
  return 'desconocido';
}

/**
 * Lo que el componente `Degracion.svelte` necesita para pintar.
 *
 * `ultimaFase` es el texto YA REDACTADO de la última fase alcanzada, no su
 * identificador: el contrato §4.1 dice que el texto lo compone el servidor, y
 * enseñar «comprobando» en crudo sería el cliente redactando.
 *
 * @param {unknown} error         lo que se atrapó
 * @param {{texto: string}|null} ultimaFase  la última fase que llegó a emitirse
 */
export function describir(error, ultimaFase = null) {
  const clase = clasificar(error);
  const m = mensajeDe(clase);
  return {
    // §8.3. La situación del contrato, no la clase interna: el componente
    // pinta por situación y las tres del contrato tienen tratamientos
    // distintos que no se pueden confundir.
    situacion: 'degradado',
    clase,
    titulo: m.titulo,
    explicacion: m.detalle,
    salida: m.salida,
    ultima_fase: ultimaFase?.texto ?? '',
    // Reintentar no se ofrece cuando repetir lleva al mismo rechazo: sin
    // sesión hay que entrar, sin permiso no hay nada que reintentar, y una
    // ruta retirada no vuelve. El mantenimiento SÍ es reintentable: es
    // transitorio por definición y `Retry-After` lo dice.
    reintentable: !['sin-sesion', 'sin-permiso', 'retirada'].includes(clase)
  };
}

/**
 * `RP-17` en una función: una respuesta degradada no arrastra contenido.
 *
 * Se aplica a lo que llega del servidor ANTES de que ningún componente lo vea.
 * Si el cuerpo trae bloques junto a una degradación, los bloques se descartan
 * y se deja constancia en `descartados` — callarlo escondería un incumplimiento
 * del contrato en el lado que lo está sufriendo.
 */
export function sanear(respuesta) {
  if (!respuesta?.degradado) return respuesta;
  const bloques = respuesta.cuerpo?.bloques ?? [];
  return {
    ...respuesta,
    cuerpo: null,
    degradado: {
      ...respuesta.degradado,
      situacion: 'degradado',
      descartados: bloques.length
    }
  };
}
