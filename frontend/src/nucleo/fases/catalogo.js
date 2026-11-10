/**
 * La lista CERRADA de fases anunciables.
 *
 * Contiene los identificadores admitidos por `DD-11` y nada más. Una fase que
 * llegue del servidor y no esté aquí NO se pinta. Es una segunda barrera para
 * `RP-18`: si algún día el backend emitiera una fase que nombra la detección o
 * el modelo del estudiante, el cliente la descarta.
 *
 * LA REGLA, y no se relaja:
 *
 *     Se anuncia QUE HACE EL SISTEMA, nunca QUE INFIERE SOBRE EL ESTUDIANTE.
 *
 * «Resolviendo el ejercicio» sí. «Detectando tu concepción errónea» no, porque
 * le comunica al estudiante que se le está diagnosticando, que es exactamente
 * lo que RP-18 prohíbe exponerle.
 *
 * Ampliar esta lista es MODIFICAR DD-11, no añadir una constante. Antes de
 * tocarla, lea OE3-Implementacion/08-Contrato-del-Turno.md §4.1 y §7.2.
 *
 * El TEXTO no se usa para pintar: lo compone el servidor y viaja en la fase.
 * Está aquí solo como referencia de lo que cada identificador significa, y
 * como respaldo si el servidor lo omitiera.
 *
 */

/** Las seis fases admitidas. Ni una más sin cambiar DD-11. */
export const CATALOGO = Object.freeze({
  leyendo:      'Leyendo tu mensaje',
  interpretando:'Interpretando la fórmula',
  resolviendo:  'Resolviendo el ejercicio',
  recuperando:  'Buscando material del curso',
  redactando:   'Redactando la respuesta',
  comprobando:  'Comprobando cada afirmación'
});

/** Los identificadores, para las pruebas y para la comprobación de contrato. */
export const ADMITIDAS = Object.freeze(Object.keys(CATALOGO));

/**
 * ¿El servidor puede anunciar esta fase?
 *
 * @param {string} id  identificador que llegó del servidor
 * @returns {boolean}
 */
export function admitida(id) {
  return Object.prototype.hasOwnProperty.call(CATALOGO, id);
}

/**
 * Deja una fase del servidor lista para pintar, o la descarta.
 *
 * Devuelve `null` cuando el identificador no está en el catálogo. Quien llame
 * DEBE tratar el nulo como «no pintar», no como «pintar vacío»: pintar una
 * fase desconocida sin texto dejaría un hueco que el estudiante interpretaría
 * como que el sistema se detuvo.
 *
 * @param {{fase: string, texto?: string}} recibida
 * @returns {{id: string, texto: string} | null}
 */
export function normalizar(recibida) {
  if (!recibida || !admitida(recibida.fase)) return null;
  return {
    id: recibida.fase,
    // El servidor compone el texto. El catálogo solo respalda si lo omitió.
    texto: recibida.texto || CATALOGO[recibida.fase]
  };
}
