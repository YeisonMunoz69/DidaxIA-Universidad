/**
 * Navegación del navegador y frontera de árboles, sin cargar la tabla de rutas.
 *
 * Los componentes necesitan cambiar de pantalla, pero no necesitan conocer ni
 * ejecutar las guardas. Mantener esta pieza libre de `rutas.js` evita que una
 * pantalla cargada de forma diferida vuelva a importarse a sí misma.
 *
 */
/**
 * El árbol al que pertenece un rol EN UN ESPACIO. Una sola frontera, la que
 * protege algo.
 *
 * ⚠️ **Se reexporta desde `espacios.js` y ya no se calcula aquí** · `EQ-031`.
 * Hasta la Fase 7 era `esEstudiante(rol) ? …`, y eso ataba el árbol al rol de
 * por vida: un docente no podía montar la conversación sin dejar de ser
 * docente. Ahora lo decide el espacio activo, y la frontera de `DD-04` sigue
 * intacta —lo que separa los dos árboles no cambió, cambió quién la cruza—.
 *
 * Vive reexportado y no reimplementado porque este módulo sigue teniendo su
 * razón de ser: los componentes necesitan `arbolDe()` y `navegar()` sin cargar
 * la tabla de rutas, para que una pantalla diferida no vuelva a importarse a sí
 * misma. `espacios.js` tampoco carga esa tabla, así que la propiedad se conserva.
 */
export { arbolDe } from './espacios.js';

/** Cambia de pantalla y notifica a la raíz para que aplique sus guardas. */
let proteccionDeSalida = null;
let salidaPendiente = false;

/** Protección optativa del editor. Sin ella, la navegación sigue síncrona. */
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
