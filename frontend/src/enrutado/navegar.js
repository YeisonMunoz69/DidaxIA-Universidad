export { arbolDe } from './espacios.js';

let proteccionDeSalida = null;
let salidaPendiente = false;

export function protegerSalida(comprobar) {
  proteccionDeSalida = comprobar;
  return () => { if (proteccionDeSalida === comprobar) proteccionDeSalida = null; };
}

export function navegar(destino, { alAceptar = () => {} } = {}) {
  const actual = `${globalThis.location?.pathname ?? ''}${globalThis.location?.search ?? ''}${globalThis.location?.hash ?? ''}`;
  if (actual === destino) return;
  function continuar() {
    alAceptar();
    globalThis.history?.pushState({}, '', destino);
    globalThis.dispatchEvent?.(new PopStateEvent('popstate'));
  }
  if (!proteccionDeSalida) { continuar(); return; }
  if (salidaPendiente) return;
  salidaPendiente = true;
  return Promise.resolve(proteccionDeSalida(destino)).then((aceptada) => {
    if (aceptada) continuar();
  }).finally(() => { salidaPendiente = false; });
}
