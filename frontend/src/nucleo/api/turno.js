/**
 * Envío del turno y recepción por partes.
 *
 * Envía el turno del estudiante y recibe la emisión por partes de DD-11:
 * primero la secuencia de fases, al final la respuesta completa con sus
 * bloques y sus sellos. No interpreta nada de lo que recibe.
 *
 * TRES COSAS SE ENVÍAN, Y DOS MÁS SOLO SI APLICAN · CONTRATO §3 y §3.ter
 * ---------------------------------------------------------------------------
 * `sesion`, `mensaje` y `momento`, más `notacion` **cuando el estudiante ha
 * elegido una** (`D-21`, `PM-B32`) y `retomar_sesion` **cuando este turno
 * escribe directamente en un hilo pasado** —`Conversacion.svelte::enviar`,
 * en TODOS los turnos de la retoma y no solo el primero: es también a qué
 * conversación se archiva cada uno, ver `rutas/turno.py`. Si no se está
 * retomando, el campo no se manda: no se envía el defecto del cliente, porque
 * entonces habría un defecto en cada lado y cambiar el del servidor dejaría
 * de cambiar nada. En particular:
 *
 *   · EL CLIENTE NO DICE QUIÉN ACERTÓ. Al contestar un ítem de dos niveles
 *     manda `nodo`, `resultado` y `razon`, y nada más: `es_correcta`, la
 *     concepción y el nivel los resuelve el servidor contra su banco. Con
 *     esos campos en el cuerpo, el estudiante se diagnosticaría a sí mismo.
 *   · EL CLIENTE NO NORMALIZA. `RP-01` obliga a normalizar a forma canónica
 *     única ANTES de procesar, y esa normalización es del servidor. Si el
 *     cliente reescribiera la entrada habría dos normalizadores y la garantía
 *     de forma única dejaría de serlo. Aquí ni se recorta ni se colapsan
 *     espacios: va lo que se escribió.
 *   · EL CLIENTE NO TRADUCE LA NOTACIÓN QUE RECIBE. Elige cuál quiere y la
 *     manda; quien escribe la fórmula sigue siendo el motor simbólico.
 *     Reescribir aquí el LaTeX que llega sería el mismo error que normalizar
 *     la entrada, con la misma consecuencia: dos autoridades sobre la misma
 *     forma. Ver `nucleo/formato/notaciones.js`.
 *   · EL CLIENTE NO MIDE LA LATENCIA DEL ESTUDIANTE. `RP-03` exige separarla
 *     de la del sistema y conservar las dos, y solo el servidor conoce ambas.
 *     `momento` es una marca de tiempo, no una medición.
 *
 * LO QUE SE HACE CON LO QUE LLEGA, Y POR QUÉ ES TAN POCO
 * ------------------------------------------------------
 * Dos cosas, las dos negativas, y las dos del contrato:
 *
 *   1. Una fase fuera del catálogo cerrado NO SE PINTA. La descarta
 *      `normalizar()` de `nucleo/fases/catalogo.js`, que es la segunda
 *      barrera de `RP-18`: si algún día el backend emitiera «detectando la
 *      concepción», el cliente la tira en vez de anunciársela al estudiante.
 *   2. Una respuesta degradada NO ARRASTRA BLOQUES. Lo garantiza `sanear()`
 *      aunque el servidor los mande.
 *
 * Todo lo demás se entrega tal cual. El sello no se interpreta, el nivel no se
 * escala y el tipo de bloque no se traduce: eso es dominio y vive en el
 * servidor. Cualquier decisión que aparezca en este archivo es una decisión en
 * el lado equivocado.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 */
import { RUTAS, pedirPorPartes } from './cliente.js';
import { normalizar } from '../fases/catalogo.js';
import { sanear } from '../errores/degradacion.js';
import { paraEnviar } from '../formato/notaciones.js';

/**
 * La generación remota tiene un presupuesto mayor que una consulta normal.
 * El servidor corta primero (60 s por defecto) y devuelve una causa trazable;
 * el navegador deja 15 s de margen para recibir esa respuesta, en vez de
 * abortar a los mismos 30 s y convertir dos situaciones distintas en una.
 */
export const ESPERA_TURNO_MS = 75_000;

/**
 * La respuesta al ítem, reducida a lo que el contrato admite.
 *
 * Devuelve `null` si falta cualquiera de los tres. Un ítem a medias no se
 * completa con supuestos: el servidor lo trataría como no diagnosticable de
 * todas formas, y así el motivo que sale en su traza es el de verdad.
 *
 * @param {{nodo?: string, resultado?: string, razon?: string} | null} respuesta
 */
function soloElContrato(respuesta) {
  const nodo = String(respuesta?.nodo ?? '').trim();
  const resultado = String(respuesta?.resultado ?? '').trim();
  const razon = String(respuesta?.razon ?? '').trim();
  if (!nodo || !resultado || !razon) return null;
  return { nodo, resultado, razon };
}

/**
 * Envía un turno y va entregando las fases conforme llegan.
 *
 * @param {{sesion: string, mensaje: string, notacion?: string, retomarSesion?: string,
 *          dosNiveles?: {nodo: string, resultado: string, razon: string} | null}} entrada
 * @param {{alFase?: (f: {id: string, texto: string}) => void,
 *          señal?: AbortSignal}} opciones
 * @returns {Promise<{fases: object[], cuerpo: object|null, degradado: object|null}>}
 */
export async function enviarTurno(
  { sesion, mensaje, notacion = '', retomarSesion = '', dosNiveles = null, idempotencia = '' },
  { alFase, señal } = {}
) {
  const fases = [];
  let cuerpo = null;
  let degradado = null;

  /** Una fase admitida se acumula y se entrega; una prohibida se descarta. */
  const anotarFase = (recibida) => {
    const f = normalizar(recibida);
    if (!f) return false;
    fases.push(f);
    alFase?.(f);
    return true;
  };

  /**
   * Cada parte del flujo, sea cual sea su forma.
   *
   * Se aceptan las dos que `cliente.js` puede entregar sin preguntar cuál
   * vino: una fase suelta, o el documento entero con `fases`, `cuerpo` y
   * `degradado`. §12 del contrato deja el mecanismo sin decidir, así que
   * depender de una sola forma sería depender de una decisión que no se ha
   * tomado.
   */
  const parte = (p) => {
    if (!p || typeof p !== 'object') return;
    if (typeof p.fase === 'string') anotarFase(p);
    if (Array.isArray(p.fases)) for (const f of p.fases) anotarFase(f);
    if (p.cuerpo) cuerpo = p.cuerpo;
    if (p.degradado) degradado = p.degradado;
  };

  await pedirPorPartes(RUTAS.turno, {
    cuerpo: {
      sesion,
      // Sin `trim()` y sin reescribir. Ver la cabecera: normalizar es del
      // servidor, y hacerlo «solo un poquito» aquí es hacerlo dos veces.
      mensaje,
      momento: new Date().toISOString(),
      // §3.ter. Ausente cuando no se eligió, y `paraEnviar` es quien lo
      // garantiza: una notación fuera del catálogo sale vacía y el campo no
      // llega a ponerse.
      ...(paraEnviar(notacion) ? { notacion: paraEnviar(notacion) } : {}),
      // Ausente cuando no se está retomando un hilo pasado —viaja en TODOS
      // los turnos de una retoma, no solo el primero, porque es también a
      // qué conversación se archiva este turno. El servidor decide solo
      // por su cuenta cuándo resembrar desde Postgres (`retomando_activo`
      // en `rutas/turno.py`), así que mandarlo de más aquí no repite esa
      // consulta.
      ...(retomarSesion ? { retomar_sesion: retomarSesion } : {}),
      // §3.quater · la clave de idempotencia del turno. Ausente cuando no se
      // manda ninguna, como el resto de campos opcionales: el servidor la
      // trata como un turno sin protección de reintento, no como un error.
      ...(idempotencia ? { idempotencia } : {}),
      // §3.bis · la respuesta a un ítem de dos niveles, cuando el estudiante
      // contestó uno. TRES CAMPOS Y NINGUNO MÁS, y `soloElContrato` es quien
      // lo garantiza: si el cliente pudiera mandar `es_correcta` o la
      // concepción, el estudiante se diagnosticaría a sí mismo escribiendo un
      // campo. Es la misma regla por la que las señales del arbitraje no
      // viajan desde el navegador.
      ...(soloElContrato(dosNiveles) ? { dos_niveles: soloElContrato(dosNiveles) } : {})
    },
    alParte: parte,
    señal,
    espera: ESPERA_TURNO_MS
  });

  // `RP-17` · §8.3. Si vino degradación, los bloques no pasan de aquí.
  const respuesta = sanear({ fases, cuerpo, degradado });

  if (!respuesta.cuerpo && !respuesta.degradado) {
    // Ni cuerpo ni degradación es una respuesta que el contrato no contempla:
    // §4.2 y §8 son excluyentes y exhaustivos. Se declara como turno
    // interrumpido —que es lo que de hecho pasó— en vez de devolver un turno
    // vacío que la conversación pintaría como si fuera una respuesta.
    return {
      ...respuesta,
      degradado: {
        situacion: 'degradado',
        ultima_fase: fases.length ? fases[fases.length - 1].texto : '',
        explicacion: 'la respuesta llegó incompleta'
      }
    };
  }
  return respuesta;
}
