
export const CATALOGO = Object.freeze({
  leyendo:      'Leyendo tu mensaje',
  interpretando:'Interpretando la fórmula',
  resolviendo:  'Resolviendo el ejercicio',
  recuperando:  'Buscando material del curso',
  redactando:   'Redactando la respuesta',
  comprobando:  'Comprobando cada afirmación'
});

export const ADMITIDAS = Object.freeze(Object.keys(CATALOGO));

export function admitida(id) {
  return Object.prototype.hasOwnProperty.call(CATALOGO, id);
}

export function normalizar(recibida) {
  if (!recibida || !admitida(recibida.fase)) return null;
  return {
    id: recibida.fase,
    texto: recibida.texto || CATALOGO[recibida.fase]
  };
}
