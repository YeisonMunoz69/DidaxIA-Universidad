/**
 * El texto de una isla de fórmula, partido en segmentos editables. `PM-F2x`
 * fase 6.
 *
 * Envuelve `segmentarNotacion()` —no reimplementa qué es notación—: dos
 * definiciones de qué cuenta como `$…$` acaban discrepando, y su propia
 * cabecera ya lo explica para el resaltado de hoy. Aquí el mismo análisis
 * sirve para decidir dónde nace una isla de `MathLive`.
 *
 * LA GARANTÍA QUE IMPORTA — `RP-01` — LA SOSTIENE EL ROUND-TRIP
 * ------------------------------------------------------------------
 * `serializar(aSegmentos(texto)) === texto` para cualquier `texto`, sin
 * excepción, en el análisis documental predeterminado. Lo que llega a
 * `alEnviar()` tiene que ser exactamente lo que
 * el estudiante escribió; si esta propiedad falla para un solo caso, el
 * editor puede reescribir en silencio lo que se envía — el peor modo de
 * fallo que la cabecera de `Redactor.svelte` ya declara. Por eso
 * `segmentos.prueba.js` la ejercita sobre el mismo banco de cadenas que ya
 * protege `redactor.prueba.js` para `segmentarNotacion`, más los casos
 * propios de partir en isla y fórmula. El redactor pide explícitamente
 * `normalizarFormulas`: dentro de una marca matemática cerrada convierte la
 * escritura ASCII a LaTeX para que pegar una fracción se vea igual que
 * construirla con el tablero; la prosa alrededor sigue intacta.
 *
 * `aSegmentos` NO SE LLAMA EN CADA TECLA
 * -----------------------------------------
 * Solo al cargar un texto existente completo —al montar el campo, tras
 * limpiarlo al enviar, o al pegar—. Mientras se escribe dentro de un tramo
 * de texto, quien edita es el propio `contenteditable` del navegador, y la
 * lista de segmentos se actualiza con una operación quirúrgica (partir uno
 * en tres al cerrar un `$…$`) y no con un re-análisis completo — eso es lo
 * que evita que Svelte reescriba el nodo y el cursor salte al principio.
 * Ver el diseño de la tanda 6c en el plan.
 *
 */
import { normalizarParaPresentacion, segmentarNotacion } from './notacion.js';

/** Contador propio y no `crypto.randomUUID()`: los ids solo tienen que ser
    únicos DENTRO de una lista, nunca entre sesiones ni persistidos, así
    que un contador es determinista —más fácil de leer en una prueba— y no
    suma una API que aquí no hace falta. */
let siguienteId = 0;

/**
 * @typedef {{ id: number, tipo: 'texto'|'formula', valor: string }} Segmento
 */

/**
 * Parte un texto completo en segmentos de texto y de fórmula.
 *
 * `valor` de un segmento `'formula'` NO lleva los delimitadores `$…$` — es
 * el LaTeX desnudo que espera `<math-field>.value` (`IslaDeFormula.svelte`).
 * Quien los vuelve a poner es `serializar`.
 *
 * @param {string} texto
 * @param {{normalizarFormulas?: boolean}} opciones
 * @returns {Segmento[]}
 */
export function aSegmentos(texto, { normalizarFormulas = false } = {}) {
  return segmentarNotacion(texto).map((trozo) => ({
    id: siguienteId++,
    tipo: trozo.marcado ? 'formula' : 'texto',
    valor: trozo.marcado
      ? (normalizarFormulas
          ? normalizarParaPresentacion(trozo.valor.slice(1, -1))
          : trozo.valor.slice(1, -1))
      : trozo.valor
  }));
}

/**
 * Un id nuevo, del mismo contador que usa `aSegmentos`.
 *
 * Para cuando quien orquesta el campo mixto —`Redactor.svelte`— construye un
 * segmento a mano: partir uno en tres al cerrar una fórmula, fusionar dos
 * tramos de texto al borrar la isla que los separaba, o empezar el campo
 * vacío. Siempre id NUEVO y nunca reutilizado, aunque el contenido sea el
 * mismo: es lo que hace que Svelte monte el nodo de cero y su contenido se
 * escriba una sola vez, en vez de reescribir uno que ya existe con el
 * estudiante escribiendo dentro.
 *
 * @returns {number}
 */
export function nuevoIdDeSegmento() {
  return siguienteId++;
}

/**
 * El camino inverso: de segmentos a la cadena exacta que se envía.
 *
 * @param {Segmento[]} segmentos
 * @returns {string}
 */
export function serializar(segmentos) {
  return segmentos
    .map((s) => (s.tipo === 'formula' ? `$${s.valor}$` : s.valor))
    .join('');
}
