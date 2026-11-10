import { mount } from 'svelte';

import './estilos/tokens.css';
import './estilos/base.css';
import './estilos/tipografia.css';

import { SUPERFICIE_PUBLICA, superficieActual } from './nucleo/configuracion/superficie.js';

const raiz =
  superficieActual() === SUPERFICIE_PUBLICA
    ? import('./presencia/Presencia.svelte')
    : import('./Aplicacion.svelte');

export default raiz.then((modulo) =>
  mount(modulo.default, {
    target: document.getElementById('aplicacion')
  })
);
