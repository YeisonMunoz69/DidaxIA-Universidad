/**
 * Punto de entrada.
 *
 * Monta el componente raíz sobre el anclaje de indice.html y carga los
 * estilos. No contiene lógica: **elegir superficie no es lógica de este
 * archivo**, la decide `nucleo/configuracion/superficie.js` y aquí sólo se
 * obedece.
 *
 * El orden de importación de los estilos importa: tokens primero, porque
 * base.css consume sus variables. Los cargan las dos superficies —los tokens y
 * la tipografía son los mismos, que es lo que `D0` §10.1 pide al hablar de
 * «diseño coherente con la aplicación existente»— y no arrastran nada de
 * JavaScript.
 *
 * ⚠️ LAS DOS RAÍCES SE IMPORTAN CON `import()`, Y NO ES UNA OPTIMIZACIÓN
 * ------------------------------------------------------------------------
 * Con `import Aplicacion from './Aplicacion.svelte'` estático, el paquete de
 * entrada contendría el árbol del tutor entero —sesión, guardas, historial,
 * Google Identity, las pantallas de estudiante y docente— y `didaxia.pro` lo
 * descargaría al abrir la portada, aunque no montara nada de eso. La
 * separación dejaría de ser comprobable: «no se usa» no es lo mismo que «no
 * llega a la máquina», y `07-Estructura-del-Frontend.md` §9 ya tomó esa misma
 * decisión para separar el árbol del docente del árbol del estudiante.
 *
 * Con `import()` cada superficie es su propio trozo y sólo se descarga el que
 * se monta. `pruebas/contrato/superficie-publica.prueba.js` comprueba que este
 * archivo no importe ninguna de las dos raíces de forma estática.
 *
 */
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
