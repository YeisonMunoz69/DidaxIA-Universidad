
function seleccionDentroDe(span) {
  const seleccion = window.getSelection();
  if (!seleccion || seleccion.rangeCount === 0) return null;
  const rango = seleccion.getRangeAt(0);
  return span.contains(rango.startContainer) ? { seleccion, rango } : null;
}

export function posicionDelCaret(span) {
  const actual = seleccionDentroDe(span);
  if (!actual) return 0;
  const previo = document.createRange();
  previo.selectNodeContents(span);
  previo.setEnd(actual.rango.startContainer, actual.rango.startOffset);
  return previo.toString().length;
}

export function colocarCaretEnPosicion(span, posicion) {
  span.focus();
  const seleccion = window.getSelection();
  if (!seleccion) return;

  try {
    if (!span.firstChild || span.firstChild.nodeType !== Node.TEXT_NODE) {
      span.textContent = '';
      span.appendChild(document.createTextNode(''));
    }
    const nodoTexto = span.firstChild;
    const maximo = nodoTexto.textContent?.length ?? 0;
    const posicionValida = Math.min(Math.max(0, posicion), maximo);
    const rango = document.createRange();
    rango.setStart(nodoTexto, posicionValida);
    rango.collapse(true);
    seleccion.removeAllRanges();
    seleccion.addRange(rango);
  } catch {
    try {
      const rango = document.createRange();
      rango.selectNodeContents(span);
      rango.collapse(false);
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
    } catch {
    }
  }
}

export function colocarCaret(span, extremo) {
  const posicion = extremo === 'inicio' ? 0 : (span.textContent?.length ?? 0);
  colocarCaretEnPosicion(span, posicion);
}

export function enfocarSegmentoEnDOM(campoMixto, segmentos, indice, extremo) {
  const segmento = segmentos[indice];
  if (!segmento) return;
  const nodo = campoMixto.querySelector(`[data-segmento-id="${segmento.id}"]`);
  if (!nodo) return;

  if (segmento.tipo === 'texto') {
    colocarCaret( (nodo), extremo);
    return;
  }

  const campoMatematico =  (nodo.querySelector('math-field'));
  campoMatematico?.focus?.();
  campoMatematico?.executeCommand?.([
    extremo === 'inicio' ? 'moveToMathfieldStart' : 'moveToMathfieldEnd'
  ]);
}

export function insertarTextoEnSeleccion(texto) {
  const seleccion = window.getSelection();
  if (!seleccion || seleccion.rangeCount === 0) return false;
  const rango = seleccion.getRangeAt(0);
  rango.deleteContents();
  const nodo = document.createTextNode(texto);
  rango.insertNode(nodo);
  if (texto.endsWith('\n') && !nodo.nextSibling?.textContent) {
    nodo.parentNode?.insertBefore(document.createElement('br'), nodo.nextSibling);
  }
  rango.setStart(nodo, texto.length);
  rango.collapse(true);
  seleccion.removeAllRanges();
  seleccion.addRange(rango);
  return true;
}

export function contenidoInicial(nodo, valor) {
  nodo.textContent = valor;
}
