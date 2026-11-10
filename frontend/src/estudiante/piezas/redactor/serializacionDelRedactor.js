/**
 * Lee el mensaje directamente del DOM del redactor.
 *
 * La lista reactiva gobierna la estructura; esta lectura conserva el valor que
 * el navegador y MathLive tienen en el instante exacto de enviar.
 */

/** @param {HTMLDivElement | undefined} campoMixto */
export function serializarDesdeDOM(campoMixto) {
  if (!campoMixto) return '';
  let resultado = '';
  for (const hijo of campoMixto.children) {
    if (hijo.classList.contains('segmento-formula')) {
      const campoMatematico = /** @type {any} */ (hijo.querySelector('math-field'));
      resultado += `$${campoMatematico?.value ?? ''}$`;
    } else {
      resultado += hijo.textContent ?? '';
    }
  }
  return resultado;
}
