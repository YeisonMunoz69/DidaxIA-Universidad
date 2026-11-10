import { normalizarParaPresentacion, segmentarNotacion } from './notacion.js';

let siguienteId = 0;


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

export function nuevoIdDeSegmento() {
  return siguienteId++;
}

export function serializar(segmentos) {
  return segmentos
    .map((s) => (s.tipo === 'formula' ? `$${s.valor}$` : s.valor))
    .join('');
}
