/**
 * Las rutas de la superficie pública. **No es `enrutado/rutas.js`.**
 *
 * ⚠️ **Y NO SE AÑADEN A AQUÉLLA, QUE ES LO QUE ESTE ARCHIVO EXISTE PARA
 * EVITAR.** `enrutado/rutas.js` es la tabla del tutor: cada entrada declara un
 * árbol —estudiante o no-estudiante—, la guardan `guardas.js` con el acceso
 * calculado por el servidor, y sus componentes se cargan con `import()`
 * diferido para que el navegador de un estudiante no descargue el árbol del
 * docente. Meter la portada ahí habría obligado a inventarle un árbol y un
 * estado de acceso a una página que no tiene ninguno de los dos, y habría
 * puesto cuatro páginas anónimas dentro de la tabla que separa lo privado.
 *
 * `D0` §10.1 declara esta superficie nueva. Es una tabla propia, con su propia
 * forma, y las dos no se tocan.
 *
 * AQUÍ LOS COMPONENTES SÍ SE IMPORTAN DIRECTO, Y ES LO CORRECTO
 * ---------------------------------------------------------------
 * En la tabla privada la carga diferida **es una barrera**: separa dos árboles
 * que no deben mezclarse en la misma descarga. Aquí no hay nada que separar
 * —las cuatro páginas son públicas, anónimas y estáticas— y partirlas en
 * cuatro descargas costaría una petición por documento a cambio de nada.
 *
 * Lo que sí está separado es esta superficie de la otra: `principal.js` importa
 * `Presencia.svelte` con `import()` y no estáticamente, así que la portada
 * nunca arrastra el árbol del tutor ni al revés.
 *
 * EL CAMINO Y EL RÓTULO SALEN DE LA CONFIGURACIÓN, NO DE AQUÍ
 * -------------------------------------------------------------
 * `nucleo/configuracion/origenes.js::PAGINAS_PUBLICAS` es la única lista de
 * caminos públicos, porque el recorrido de consentimiento también la necesita.
 * Este archivo sólo ata cada camino con su componente.
 *
 */
import { PAGINAS_PUBLICAS } from '../nucleo/configuracion/origenes.js';
import Portada from './paginas/Portada.svelte';
import Privacidad from './paginas/Privacidad.svelte';
import Condiciones from './paginas/Condiciones.svelte';
import Investigacion from './paginas/Investigacion.svelte';

/** Qué componente pinta cada camino declarado en la configuración. */
const COMPONENTES = Object.freeze({
  '/': Portada,
  '/privacidad': Privacidad,
  '/condiciones': Condiciones,
  '/investigacion': Investigacion
});

/**
 * Las páginas públicas, ya con su componente.
 *
 * Se deriva de `PAGINAS_PUBLICAS` en vez de repetir la lista: un camino nuevo
 * en la configuración sin componente aquí sale con `componente: undefined` y
 * `paginaDe()` lo trata como inexistente, que es preferible a una tabla que
 * dice tener una página y no la tiene.
 */
export const PAGINAS = Object.freeze(
  PAGINAS_PUBLICAS.map((p) => Object.freeze({ ...p, componente: COMPONENTES[p.camino] }))
);

/**
 * Normaliza un camino antes de buscarlo.
 *
 * `/privacidad/` y `/privacidad` son la misma página: un enlace pegado a mano
 * con la barra final no puede acabar en «esta dirección no existe». La raíz se
 * conserva como `/`, que sí es un camino.
 */
export function normalizar(camino) {
  const limpio = String(camino ?? '/').split('?')[0].split('#')[0];
  if (limpio.length > 1 && limpio.endsWith('/')) return limpio.replace(/\/+$/, '') || '/';
  return limpio || '/';
}

/**
 * La página de un camino, o `null`.
 *
 * Devuelve `null` y no la portada por lo mismo que `enrutado/rutas.js::rutaDe()`
 * lo hace —`T-13`—: pintar el inicio cuando se pidió otra cosa es una
 * degradación silenciosa, y la dirección tecleada se pierde antes de poder
 * copiarla para reportarla.
 */
export function paginaDe(camino) {
  const buscado = normalizar(camino);
  return PAGINAS.find((p) => p.camino === buscado && p.componente) ?? null;
}
