/**
 * Operaciones DOM de selección y caret del redactor mixto.
 *
 * Este módulo no conoce el estado de Svelte ni decide cómo cambia la lista de
 * segmentos. Su única autoridad es traducir entre una posición visible del
 * navegador y un segmento ya existente.
 */

/** @param {HTMLElement} span */
function seleccionDentroDe(span) {
  const seleccion = window.getSelection();
  if (!seleccion || seleccion.rangeCount === 0) return null;
  const rango = seleccion.getRangeAt(0);
  return span.contains(rango.startContainer) ? { seleccion, rango } : null;
}

/** @param {HTMLElement} span */
export function posicionDelCaret(span) {
  const actual = seleccionDentroDe(span);
  if (!actual) return 0;
  const previo = document.createRange();
  previo.selectNodeContents(span);
  previo.setEnd(actual.rango.startContainer, actual.rango.startOffset);
  return previo.toString().length;
}

/** @param {HTMLElement} span @param {number} posicion */
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
      // Un DOM transitorio no debe impedir que el control recupere el foco.
    }
  }
}

/** @param {HTMLElement} span @param {'inicio'|'final'} extremo */
export function colocarCaret(span, extremo) {
  const posicion = extremo === 'inicio' ? 0 : (span.textContent?.length ?? 0);
  colocarCaretEnPosicion(span, posicion);
}

/**
 * @param {HTMLElement} campoMixto
 * @param {import('../../../nucleo/formato/segmentos.js').Segmento[]} segmentos
 * @param {number} indice
 * @param {'inicio'|'final'} extremo
 */
export function enfocarSegmentoEnDOM(campoMixto, segmentos, indice, extremo) {
  const segmento = segmentos[indice];
  if (!segmento) return;
  const nodo = campoMixto.querySelector(`[data-segmento-id="${segmento.id}"]`);
  if (!nodo) return;

  if (segmento.tipo === 'texto') {
    colocarCaret(/** @type {HTMLElement} */ (nodo), extremo);
    return;
  }

  const campoMatematico = /** @type {any} */ (nodo.querySelector('math-field'));
  campoMatematico?.focus?.();
  campoMatematico?.executeCommand?.([
    extremo === 'inicio' ? 'moveToMathfieldStart' : 'moveToMathfieldEnd'
  ]);
}

/** Inserta texto plano exactamente donde está la selección actual. */
export function insertarTextoEnSeleccion(texto) {
  const seleccion = window.getSelection();
  if (!seleccion || seleccion.rangeCount === 0) return false;
  const rango = seleccion.getRangeAt(0);
  rango.deleteContents();
  const nodo = document.createTextNode(texto);
  rango.insertNode(nodo);
  // El salto final necesita una línea visible donde colocar el caret.
  // Un br auxiliar no altera textContent ni la serialización del mensaje.
  if (texto.endsWith('\n') && !nodo.nextSibling?.textContent) {
    nodo.parentNode?.insertBefore(document.createElement('br'), nodo.nextSibling);
  }
  rango.setStart(nodo, texto.length);
  rango.collapse(true);
  seleccion.removeAllRanges();
  seleccion.addRange(rango);
  return true;
}

/** Acción Svelte: el navegador recibe el contenido sólo cuando nace el nodo. */
export function contenidoInicial(nodo, valor) {
  nodo.textContent = valor;
}
