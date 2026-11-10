import { aSegmentos, nuevoIdDeSegmento } from '../../../nucleo/formato/segmentos.js';


export function segmentoDeTexto(valor) {
  return { id: nuevoIdDeSegmento(), tipo: 'texto', valor };
}

export function segmentoDeFormula(valor) {
  return { id: nuevoIdDeSegmento(), tipo: 'formula', valor };
}

export function actualizarTexto(segmentos, id, contenido) {
  const indice = segmentos.findIndex((segmento) => segmento.id === id);
  if (indice === -1) return { segmentos, foco: null };

  const actualizado = segmentos.map((segmento, posicion) =>
    posicion === indice ? { ...segmento, valor: contenido } : segmento
  );

  if (contenido === '') {
    const todosVacios = actualizado.length > 1
      && actualizado.every((segmento) => segmento.tipo === 'texto' && !segmento.valor);
    return {
      segmentos: todosVacios ? [segmentoDeTexto('')] : actualizado,
      foco: null
    };
  }

  const partes = aSegmentos(contenido, { normalizarFormulas: true });
  const cambioDeTipo = partes.length !== 1 || partes[0]?.tipo !== 'texto';
  if (!cambioDeTipo) return { segmentos: actualizado, foco: null };

  const indiceRelativoDeFormula = partes.findIndex((parte) => parte.tipo === 'formula');
  return {
    segmentos: [...segmentos.slice(0, indice), ...partes, ...segmentos.slice(indice + 1)],
    foco: { indice: indice + indiceRelativoDeFormula, extremo: 'final' }
  };
}

export function eliminarFormula(segmentos, id) {
  const indice = segmentos.findIndex((segmento) => segmento.id === id);
  if (indice === -1) return { segmentos, foco: null };

  const anterior = segmentos[indice - 1];
  const siguiente = segmentos[indice + 1];

  if (anterior?.tipo === 'texto' && siguiente?.tipo === 'texto') {
    const fusionado = segmentoDeTexto(anterior.valor + siguiente.valor);
    return {
      segmentos: [
        ...segmentos.slice(0, indice - 1),
        fusionado,
        ...segmentos.slice(indice + 2)
      ],
      foco: { id: fusionado.id, posicion: anterior.valor.length }
    };
  }

  if (anterior?.tipo === 'texto') {
    return {
      segmentos: segmentos.filter((segmento) => segmento.id !== id),
      foco: { id: anterior.id, posicion: anterior.valor.length }
    };
  }

  if (siguiente?.tipo === 'texto') {
    return {
      segmentos: segmentos.filter((segmento) => segmento.id !== id),
      foco: { id: siguiente.id, posicion: 0 }
    };
  }

  const nuevo = segmentoDeTexto('');
  const restantes = [
    ...segmentos.slice(0, indice),
    nuevo,
    ...segmentos.slice(indice + 1)
  ].filter((segmento) => segmento.id !== id);
  return {
    segmentos: restantes.length > 0 ? restantes : [nuevo],
    foco: { id: nuevo.id, posicion: 0 }
  };
}

export function insertarFormula(segmentos, indiceTexto, posicion, latex) {
  const segmento = segmentos[indiceTexto];
  const textoActual = segmento?.valor ?? '';
  const antes = segmentoDeTexto(textoActual.slice(0, posicion));
  const formula = segmentoDeFormula(latex);
  const despues = segmentoDeTexto(textoActual.slice(posicion));
  const anteriores = segmentos.slice(0, indiceTexto);

  return {
    segmentos: [
      ...anteriores,
      antes,
      formula,
      despues,
      ...segmentos.slice(indiceTexto + 1)
    ],
    foco: { indice: anteriores.length + 1, extremo: 'final' }
  };
}
