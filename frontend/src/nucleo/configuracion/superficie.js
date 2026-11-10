/**
 * Qué superficie se monta: la presencia pública o la aplicación del tutor.
 *
 * `D0` §10.1 separó las dos direcciones y este módulo es **la única pieza que
 * decide cuál se está sirviendo**. No hay ninguna otra comprobación de
 * `location.hostname` en el árbol: repartida por los componentes, cada uno
 * habría acabado con su propia lista de nombres y bastaría olvidar uno para
 * que la portada montara el tutor o al revés.
 *
 * LA DECISIÓN ES UNA FUNCIÓN PURA, Y ESO ES LO QUE LA HACE COMPROBABLE
 * ---------------------------------------------------------------------
 * `superficieDe()` no lee el navegador: recibe el nombre de servidor y el modo
 * forzado, y devuelve la superficie. `superficieActual()` es la capa delgada
 * que sí mira `location` y `import.meta.env`, y no tiene ninguna regla propia.
 *
 * EL FALLO VA HACIA LA SUPERFICIE PÚBLICA, NO HACIA LA APLICACIÓN
 * ----------------------------------------------------------------
 * Un nombre que no se reconoce —un dominio nuevo, un alias mal configurado, un
 * `Host:` inventado— recibe la **presencia pública**, que no consulta la
 * sesión, no carga Google, no habla con el backend y no importa ninguna
 * pantalla del estudiante, del docente ni del investigador. Es el mismo
 * criterio de `rol.js::esEstudiante()`: lo que no se reconoce recibe la vista
 * que no expone nada.
 *
 * Al revés —caer en la aplicación por omisión— un origen equivocado montaría
 * el árbol privado y pediría sesión desde una dirección que nadie decidió
 * publicar. Que el servidor negaría igual no lo vuelve correcto: el navegador
 * ya habría descargado el árbol y llamado a `/api/sesion`.
 *
 * ⚠️ **Y NO ES UNA BARRERA DE SEGURIDAD.** La separación real la ejerce el
 * borde HTTP —`Caddyfile`, un sitio por dominio, con `/api/*` proxificado sólo
 * en el de la aplicación— y el servidor detrás. Esto sólo decide qué se pinta.
 *
 */
import {
  HOSTNAME_APLICACION,
  ORIGEN_APLICACION,
  ORIGEN_PUBLICO
} from './origenes.js';

/** La portada y los documentos públicos. */
export const SUPERFICIE_PUBLICA = 'publica';

/** El tutor: el árbol que ya existía. */
export const SUPERFICIE_APLICACION = 'aplicacion';

/** Los nombres de bucle local. `localhost` y sus dos direcciones. */
const LOCALES = Object.freeze(['localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0']);

/**
 * Direcciones de red privada · RFC 1918.
 *
 * Cuentan como locales a propósito: el equipo prueba la aplicación desde el
 * teléfono contra `http://192.168.x.x:5173`, y sin esto esa prueba mostraría
 * la portada en vez del tutor. No debilita el fallo seguro —una dirección
 * privada no es alcanzable desde fuera de la red del equipo— y deja
 * «desconocido» significando lo que tiene que significar: un nombre público
 * que no es el de la aplicación.
 */
const PRIVADAS = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

/** ¿Este nombre de servidor es del equipo que desarrolla? */
export function esHostLocal(hostname) {
  const nombre = String(hostname ?? '').toLowerCase();
  if (!nombre) return false;
  if (LOCALES.includes(nombre)) return true;
  // `mi-equipo.localhost` resuelve a bucle local en los navegadores actuales.
  if (nombre.endsWith('.localhost')) return true;
  return PRIVADAS.test(nombre);
}

/**
 * Un nombre y su variante con `www.` son el mismo sitio.
 *
 * Quien teclee `www.didaxia.pro` tiene que ver la portada, no el árbol
 * privado por no estar en la lista.
 */
function mismoNombre(hostname, esperado) {
  if (!esperado) return false;
  return hostname === esperado || hostname === `www.${esperado}`;
}

/** Un origen absoluto sin barra final, o `''` si la configuración es ilegible. */
function origenNormalizado(origen) {
  try {
    return new URL(origen).origin.toLowerCase();
  } catch {
    return '';
  }
}

/**
 * La superficie que corresponde. **La regla completa, y no hay otra.**
 *
 * @param {{hostname?: string, origin?: string, forzada?: string,
 *   origenAplicacion?: string, origenPublico?: string}} lugar
 *   `hostname` es el nombre del servidor y `origin` incluye esquema y puerto.
 *   Hace falta conservar ambos: en la validación local la aplicación y la
 *   portada comparten `localhost`, pero escuchan en puertos distintos.
 *   `forzada` es el modo local explícito (`VITE_SUPERFICIE`).
 * @returns {'publica'|'aplicacion'}
 */
export function superficieDe({
  hostname = '',
  origin = '',
  forzada = '',
  origenAplicacion = ORIGEN_APLICACION,
  origenPublico = ORIGEN_PUBLICO
} = {}) {
  // 1 · el modo explícito manda. Es el único mecanismo para ver la portada en
  //     `localhost`, donde el nombre por sí solo diría «aplicación».
  const modo = String(forzada ?? '').trim().toLowerCase();
  if (modo === SUPERFICIE_PUBLICA) return SUPERFICIE_PUBLICA;
  if (modo === SUPERFICIE_APLICACION) return SUPERFICIE_APLICACION;

  const nombre = String(hostname ?? '').toLowerCase();
  const origen = origenNormalizado(origin);

  // 2 · un origen configurado manda antes que la regla de bucle local. En
  //     producción esto coincide con los hostnames; en local distingue
  //     `http://localhost:18080` de `http://localhost:18081`. Comparar sólo el
  //     hostname hacía que ambos montaran la aplicación y que la superficie
  //     pública llamara por error a `/api/sesion`.
  if (origen && origen === origenNormalizado(origenPublico)) {
    return SUPERFICIE_PUBLICA;
  }
  if (origen && origen === origenNormalizado(origenAplicacion)) {
    return SUPERFICIE_APLICACION;
  }

  // 3 · el equipo desarrollando. La aplicación conserva el comportamiento por
  //     defecto en `localhost`, que es el que tenía antes de este paquete.
  if (esHostLocal(nombre)) return SUPERFICIE_APLICACION;

  // 4 · la dirección de producción de la aplicación.
  if (mismoNombre(nombre, HOSTNAME_APLICACION)) return SUPERFICIE_APLICACION;

  // 5 · el dominio público **y todo lo demás**, por el mismo camino y a
  //     propósito. Una rama `if (mismoNombre(nombre, HOSTNAME_PUBLICO))`
  //     devolvería exactamente lo que devuelve este respaldo, y escrita
  //     invitaría a leer que un nombre no listado recibe otra cosa. Ver la
  //     cabecera: lo que no se reconoce recibe la superficie que no expone
  //     nada.
  return SUPERFICIE_PUBLICA;
}

/**
 * La superficie de esta pestaña. La capa delgada, sin reglas propias.
 *
 * `lugar` se puede pasar para probar sin tocar `location`, que en jsdom no es
 * reasignable.
 */
export function superficieActual(lugar = globalThis.location) {
  return superficieDe({
    hostname: lugar?.hostname ?? '',
    origin: lugar?.origin ?? '',
    forzada: import.meta.env.VITE_SUPERFICIE ?? ''
  });
}
