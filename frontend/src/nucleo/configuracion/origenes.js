/**
 * Los dos orígenes del proyecto, y el catálogo de páginas públicas.
 *
 * `D0` §10.1 fijó dos direcciones y esta es la única copia de las dos:
 *
 *   · `didaxia.pro`      la presencia pública — portada y documentos
 *   · `app.didaxia.pro`  la aplicación del tutor, que ya existía
 *
 * ⚠️ **UN SOLO SITIO, PORQUE SON ENLACES ENTRE SUPERFICIES.** La portada
 * enlaza al tutor y el recorrido de consentimiento enlaza a los documentos
 * públicos. Escritos a mano en cada componente, un despliegue de pruebas
 * dejaría la mitad de los enlaces apuntando a producción sin que nada lo
 * dijera — el mismo defecto que `configuracion/institucion.js` ya corrigió
 * para el dominio institucional.
 *
 * DE DÓNDE SALE EL VALOR
 * -----------------------
 * `vite.config.js` lee `ORIGEN_PUBLICO` y `ORIGEN_APLICACION` de
 * `process.env` y las hornea como literales dentro del paquete, igual que
 * `GOOGLE_CLIENT_ID` y `DOMINIO_INSTITUCIONAL`. Como las hornea el
 * empaquetado, tienen que estar presentes al **construir**, no al arrancar.
 *
 * Sin variables, los valores de `D0`. Un respaldo vacío dejaría enlaces rotos
 * en la portada, que es peor que apuntar a la dirección decidida.
 *
 * ⚠️ **ESTO NO ES UNA BARRERA Y NO PUEDE SERLO.** Quien pueda construir el
 * paquete puede poner aquí lo que quiera. Lo que de verdad separa las dos
 * superficies en producción es la configuración del borde —`Caddyfile`, un
 * sitio por dominio y `/api/*` proxificado sólo en el de la aplicación— y las
 * comprobaciones del servidor. Estos valores sólo deciden a dónde apunta un
 * `<a href>`.
 *
 */

/** La presencia pública. `D0` §10.1: `didaxia.pro`. */
export const ORIGEN_PUBLICO =
  import.meta.env.VITE_ORIGEN_PUBLICO || 'https://didaxia.pro';

/** La aplicación del tutor. `D0` §10.1: `app.didaxia.pro`. */
export const ORIGEN_APLICACION =
  import.meta.env.VITE_ORIGEN_APLICACION || 'https://app.didaxia.pro';

/**
 * El nombre de servidor de un origen, o `''` si no se puede leer.
 *
 * `new URL()` lanza con una cadena que no sea una dirección absoluta, y una
 * variable mal puesta al construir no puede tumbar la página entera: se
 * degrada a «no reconozco este origen», que es lo que `superficie.js`
 * necesita para caer del lado seguro.
 */
export function hostnameDe(origen) {
  try {
    return new URL(origen).hostname.toLowerCase();
  } catch {
    return '';
  }
}

/** `didaxia.pro`, ya sin esquema. Lo consume `superficie.js`. */
export const HOSTNAME_PUBLICO = hostnameDe(ORIGEN_PUBLICO);

/** `app.didaxia.pro`, ya sin esquema. Lo consume `superficie.js`. */
export const HOSTNAME_APLICACION = hostnameDe(ORIGEN_APLICACION);

/**
 * Las páginas de la presencia pública · `D0` §10.1.
 *
 * Camino, rótulo y una frase de qué contiene. **Datos, no componentes**: este
 * módulo lo importan las dos superficies —la pública para enrutar y pintar su
 * navegación, y el recorrido de consentimiento para enlazar los documentos—, y
 * si trajera los `.svelte` dentro, el paquete del tutor arrastraría la portada
 * entera por citar tres enlaces. Los componentes los ata `presencia/rutas.js`,
 * que sólo vive del lado público.
 *
 * `/` no lleva `documento: true`: es la portada, no uno de los tres textos que
 * el consentimiento enlaza.
 */
export const PAGINAS_PUBLICAS = Object.freeze([
  Object.freeze({
    camino: '/',
    titulo: 'Inicio',
    resumen: 'Qué es DidaxIa, quién lo hace y para qué sirve.'
  }),
  Object.freeze({
    camino: '/privacidad',
    titulo: 'Privacidad',
    documento: true,
    resumen: 'Qué datos se prevén, para qué, quién los ve y qué derechos hay.'
  }),
  Object.freeze({
    camino: '/condiciones',
    titulo: 'Condiciones',
    documento: true,
    resumen: 'Cómo se accede, qué alcance tiene el tutor y qué se espera de quien lo usa.'
  }),
  Object.freeze({
    camino: '/investigacion',
    titulo: 'Investigación',
    documento: true,
    resumen: 'El objetivo del proyecto, el piloto y qué se publica de él.'
  })
]);

/** Los tres textos que el recorrido de consentimiento enlaza. */
export const DOCUMENTOS_PUBLICOS = Object.freeze(
  PAGINAS_PUBLICAS.filter((p) => p.documento)
);

/**
 * Un camino de la presencia pública, ya con su origen delante.
 *
 * Hace falta cuando el enlace se pinta **desde la aplicación**: allí un
 * `/privacidad` relativo apuntaría a `app.didaxia.pro/privacidad`, que no
 * existe. Dentro de la propia superficie pública se usan caminos relativos,
 * que es lo que `presencia/` hace.
 */
export function enlacePublico(camino) {
  return `${ORIGEN_PUBLICO}${camino === '/' ? '' : camino}`;
}

/** La acción principal de la portada: entrar al tutor. */
export const ENLACE_AL_TUTOR = ORIGEN_APLICACION;
