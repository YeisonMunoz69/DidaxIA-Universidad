/**
 * Los caminos de la biblioteca de fuentes, y el retorno al turno.
 *
 * EL PARÁMETRO `volver` ES EL ÚNICO SITIO POR DONDE ENTRARÍA UN OPEN REDIRECT
 * ----------------------------------------------------------------------------
 * El estudiante sale de la conversación a leer una fuente y tiene que poder
 * volver exactamente a donde estaba. La forma barata de hacerlo es llevar el
 * camino en la URL —`?volver=/`— y la forma peligrosa de leerlo es confiar en
 * él: `?volver=https://sitio-falso` convertiría un botón «Volver a la
 * conversación» en un enlace a otro dominio, con la credibilidad de estar
 * dentro de la aplicación.
 *
 * `destinoDeRetorno()` **no sanea la cadena: la comprueba contra una lista**.
 * Lo que no sea un camino interno conocido se descarta y se devuelve el inicio,
 * que es un destino seguro y honesto. Sanear —quitar `http://`, quitar `//`—
 * es la técnica que siempre deja una forma más que nadie previó; comprobar
 * contra la tabla de rutas que la aplicación ya declara, no.
 *
 * Se admite además el ancla del turno (`#turno-…`), porque volver «al turno» y
 * volver «a la conversación» no son lo mismo para quien tenía veinte mensajes
 * arriba. El ancla se acota a la forma que el turno emite.
 *
 */
import { CAMINOS, inicioDe } from '../../enrutado/caminos.js';

/** Forma del ancla de un turno, tal como la escribe `Turno.svelte`. */
const ANCLA = /^[A-Za-z0-9_-]{1,64}$/;

/** El nombre del parámetro. Uno solo, y se escribe aquí. */
export const PARAMETRO_DE_RETORNO = 'volver';

/**
 * ¿Es este un camino interno al que la aplicación puede volver?
 *
 * Se compara contra `CAMINOS`, el catálogo sin componentes del que también se
 * construye `RUTAS`. Una ruta nueva se declara una sola vez y una inventada no
 * pasa; además, el lector no tiene que importar el árbol de pantallas.
 */
export function esCaminoInterno(camino) {
  if (typeof camino !== 'string' || !camino.startsWith('/')) return false;
  // `//evil.example` empieza por barra y es un URL absoluto de protocolo
  // relativo: el navegador lo resolvería a otro dominio. Es el caso que una
  // comprobación de «empieza por /» sola deja pasar.
  if (camino.startsWith('//')) return false;
  if (camino.includes('\\')) return false;

  const [base, ancla] = camino.split('#', 2);
  if (ancla !== undefined && !ANCLA.test(ancla)) return false;
  // Sin parámetros: el retorno lleva a una pantalla, no a un estado con
  // consulta. Admitirlos abriría la puerta a anidar otro `volver` dentro.
  if (base.includes('?')) return false;

  return Object.values(CAMINOS).includes(base);
}

/**
 * El camino al que volver, o el inicio del rol si lo pedido no es admisible.
 *
 * **Nunca devuelve `null`**: quien llama tiene siempre un sitio a donde ir, y
 * una función que a veces no decide obliga a repetir el criterio en cada
 * pantalla — repetido, acaba divergiendo.
 */
export function destinoDeRetorno(pedido, rol = 'estudiante') {
  return esCaminoInterno(pedido) ? pedido : inicioDe(rol);
}

/** El camino de la ficha de un fragmento, con su retorno si lo hay. */
export function caminoDeFuente(id, volverA) {
  const base = `/fuentes/${encodeURIComponent(id)}`;
  if (!esCaminoInterno(volverA)) return base;
  return `${base}?${PARAMETRO_DE_RETORNO}=${encodeURIComponent(volverA)}`;
}

/** El camino de la lectura de una obra, opcionalmente en una parte. */
export function caminoDeObra(clave, { parte, fragmento, volverA, vista } = {}) {
  const parametros = new URLSearchParams();
  if (parte) parametros.set('parte', parte);
  if (fragmento) parametros.set('fragmento', fragmento);
  if (vista === 'original') parametros.set('vista', 'original');
  if (esCaminoInterno(volverA)) parametros.set(PARAMETRO_DE_RETORNO, volverA);
  const consulta = parametros.toString();
  return `/obras/${encodeURIComponent(clave)}${consulta ? `?${consulta}` : ''}`;
}

/**
 * El identificador que lleva un camino de fuente, o `''`.
 *
 * Se lee del camino y **no del estado del componente**: es lo que hace que el
 * enlace profundo funcione al recargar, que es media Fase 5.
 */
export function fragmentoDelCamino(camino) {
  const partes = String(camino ?? '').split('?')[0].split('/');
  return partes[1] === 'fuentes' && partes[2] ? decodeURIComponent(partes[2]) : '';
}

/** La clave de obra que lleva un camino de obra, o `''`. */
export function obraDelCamino(camino) {
  const partes = String(camino ?? '').split('?')[0].split('/');
  return partes[1] === 'obras' && partes[2] ? decodeURIComponent(partes[2]) : '';
}
