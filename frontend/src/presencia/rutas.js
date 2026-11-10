import { PAGINAS_PUBLICAS } from '../nucleo/configuracion/origenes.js';
import Portada from './paginas/Portada.svelte';
import Privacidad from './paginas/Privacidad.svelte';
import Condiciones from './paginas/Condiciones.svelte';
import Investigacion from './paginas/Investigacion.svelte';

const COMPONENTES = Object.freeze({
  '/': Portada,
  '/privacidad': Privacidad,
  '/condiciones': Condiciones,
  '/investigacion': Investigacion
});

export const PAGINAS = Object.freeze(
  PAGINAS_PUBLICAS.map((p) => Object.freeze({ ...p, componente: COMPONENTES[p.camino] }))
);

export function normalizar(camino) {
  const limpio = String(camino ?? '/').split('?')[0].split('#')[0];
  if (limpio.length > 1 && limpio.endsWith('/')) return limpio.replace(/\/+$/, '') || '/';
  return limpio || '/';
}

export function paginaDe(camino) {
  const buscado = normalizar(camino);
  return PAGINAS.find((p) => p.camino === buscado && p.componente) ?? null;
}
