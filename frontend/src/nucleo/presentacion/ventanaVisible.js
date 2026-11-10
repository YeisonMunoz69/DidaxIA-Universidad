/** El teclado del teléfono reduce visualViewport, aunque 100dvh no cambie.
 * No seguimos el zoom: ampliar una fórmula no debe encoger todo el armazón.
 */
export function seguirVentanaVisible(nodo) {
  const ventana = window.visualViewport;
  if (!ventana) return {};
  function ajustar() {
    if (Math.abs(ventana.scale - 1) > .01) return;
    nodo.style.setProperty('--alto-visible', `${ventana.height}px`);
    nodo.style.setProperty('--desplazamiento-visible', `${ventana.offsetTop}px`);
  }
  ajustar();
  ventana.addEventListener('resize', ajustar);
  ventana.addEventListener('scroll', ajustar);
  return { destroy() {
    ventana.removeEventListener('resize', ajustar);
    ventana.removeEventListener('scroll', ajustar);
    nodo.style.removeProperty('--alto-visible');
    nodo.style.removeProperty('--desplazamiento-visible');
  } };
}

/** El mousedown que sigue a un toque sobre el papel no debe desenfocar el
 * editor. No se cancela pointermove/touchmove: el gesto sigue desplazando.
 */
export function conservarFocoAlLeer(nodo) {
  function conservar(evento) {
    if (!evento.sourceCapabilities?.firesTouchEvents || !document.activeElement?.closest('.campo-mixto')) return;
    if (evento.target.closest('button,a,input,textarea,select,[contenteditable="true"]')) return;
    evento.preventDefault();
  }
  nodo.addEventListener('mousedown', conservar);
  return { destroy() { nodo.removeEventListener('mousedown', conservar); } };
}
