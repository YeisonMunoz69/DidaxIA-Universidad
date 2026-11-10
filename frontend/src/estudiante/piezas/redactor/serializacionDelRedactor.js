
export function serializarDesdeDOM(campoMixto) {
  if (!campoMixto) return '';
  let resultado = '';
  for (const hijo of campoMixto.children) {
    if (hijo.classList.contains('segmento-formula')) {
      const campoMatematico =  (hijo.querySelector('math-field'));
      resultado += `$${campoMatematico?.value ?? ''}$`;
    } else {
      resultado += hijo.textContent ?? '';
    }
  }
  return resultado;
}
