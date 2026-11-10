/**
 * Empaquetado y servidor de desarrollo.
 *
 * El proxy hacia el backend existe para que el navegador vea UN SOLO ORIGEN
 * durante el desarrollo. Sin él habría que abrir CORS en el backend, y una
 * configuración de CORS puesta «para desarrollar» es de las que acaban en
 * producción sin que nadie la revise.
 *
 * ⚠️ **DOS SUPERFICIES, DOS CONFIGURACIONES DE SERVIDOR — Y UNA SOLA FÁBRICA.**
 * `npm run dev` levanta la aplicación con su proxy; `npm run dev-publico`
 * levanta la portada **sin ninguna vía hacia el backend**. Lo que cambia entre
 * las dos son tres valores —puerto, proxy y frontera— y no un archivo aparte:
 * duplicar la configuración habría dejado dos verdades que se separan a la
 * primera corrección.
 *
 * Las piezas que deciden esas tres cosas se exportan con nombre
 * —`esCaminoDeApi`, `fronteraDeApi`, `origenesPara`— para que se puedan probar
 * sin levantar un servidor, y además se levantan de verdad en
 * `pruebas/contrato/servidores-locales.prueba.js`.
 *
 */
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { presentacionIntegrada } from './empaquetado/presentacion-integrada.js';

/**
 * El documento se llama `indice.html`, no `index.html`.
 *
 * Lo fija `07-Estructura-del-Frontend.md` §2: todo en español, como el backend.
 * Vite busca `index.html` por convención, así que sin estas dos piezas ni
 * `npm run dev` ni `npm run construir` encuentran el punto de entrada — es lo
 * que pasaba hasta el 2026-08-10, cuando `PM-F02` intentó compilar por primera
 * vez y salió «Could not resolve entry module "index.html"».
 *
 * Se arregla la configuración y NO el nombre del archivo: renombrarlo sería
 * dejar que la convención de una herramienta decida el idioma del proyecto, y
 * la estructura ya tomó esa decisión al revés.
 */
const ENTRADA = fileURLToPath(new URL('./indice.html', import.meta.url));

/** El modo que activa la superficie pública local. `npm run dev-publico`. */
const MODO_PUBLICO = 'publico';

/**
 * El modo con el que Vitest resuelve esta configuración.
 *
 * No se inventa aquí: Vitest llama a la fábrica con `command: 'serve'` y
 * `mode: 'test'`. Se le da nombre para poder distinguir «estoy sirviendo para
 * una persona» de «me están resolviendo para correr pruebas», que son dos
 * cosas distintas y hasta ahora se confundían con `command`.
 */
const MODO_PRUEBAS = 'test';

/** Los puertos de las dos superficies locales. Una sola definición. */
const PUERTO_APLICACION = 5173;
const PUERTO_PUBLICO = 5174;

/**
 * ¿Este camino es del API del backend?
 *
 * Una sola definición para los dos sitios que la necesitan: la reescritura a
 * `indice.html` —que tiene que dejar pasar el API— y la frontera de la
 * superficie pública —que tiene que cerrarlo—. Escrita dos veces, la segunda
 * copia se habría olvidado de `/api` sin barra, que es justo el caso que
 * `/api/*` no cubre.
 *
 * Se recorta la cadena de consulta: `/api/salud?detalle=1` es el API.
 */
export function esCaminoDeApi(url) {
  const camino = String(url ?? '/').split('?')[0];
  return camino === '/api' || camino.startsWith('/api/');
}

/** Lo que se responde en la superficie pública a una petición del API. */
export const CUERPO_SIN_API = 'El API del tutor no se sirve en esta superficie.';

/**
 * El middleware que cierra `/api` en la superficie pública local.
 *
 * ⚠️ **ES LA MISMA FRONTERA QUE `Caddyfile` APLICA EN PRODUCCIÓN**, y existe
 * porque hasta ahora no la aplicaba: `npm run dev-publico` conservaba el proxy
 * de la aplicación, de modo que `http://localhost:5174/api/salud` **alcanzaba
 * el backend**. La portada quedaba pareciendo separada mientras tenía una
 * puerta abierta que producción sí cierra — exactamente la clase de diferencia
 * entre desarrollo y producción que se descubre tarde.
 *
 * **No llama a `siguiente()`.** Ésa es la parte que importa: `siguiente()` es
 * el único camino hacia el proxy y hacia el respaldo a `indice.html`, así que
 * terminar aquí la respuesta es lo que garantiza que la petición no llegue ni
 * al backend ni al documento HTML. Un 404 con cuerpo de texto, y no un 200 con
 * `indice.html`, es también lo que distingue «aquí no hay API» de «aquí el API
 * contesta cosas raras».
 */
export function fronteraDeApi() {
  return function cerrarApi(peticion, respuesta, siguiente) {
    if (!esCaminoDeApi(peticion?.url)) return siguiente();
    respuesta.statusCode = 404;
    respuesta.setHeader('Content-Type', 'text/plain; charset=utf-8');
    respuesta.end(CUERPO_SIN_API);
    return undefined;
  };
}

/**
 * El complemento que instala esa frontera, y sólo en la superficie pública.
 *
 * Se instala dentro de `configureServer` **sin devolver una función**, que es
 * lo que hace que corra ANTES de los middlewares internos de Vite —el proxy y
 * el respaldo de la aplicación de una sola página—. Devuelta, correría después
 * y el proxy ya habría hablado con el backend.
 *
 * `apply: 'serve'` porque en un empaquetado no hay servidor que proteger: allí
 * la frontera la ejerce `Caddyfile`.
 */
export function fronteraPublica(activa) {
  return {
    name: 'frontera-publica',
    apply: 'serve',
    configureServer(servidor) {
      if (!activa) return;
      servidor.middlewares.use(fronteraDeApi());
    }
  };
}

/**
 * El proxy hacia el backend, o **nada** en la superficie pública.
 *
 * Devolver `undefined` y no un objeto vacío es deliberado: `server.proxy` sin
 * declarar es una configuración que no puede fallar abierta, mientras que un
 * `{}` invita a que alguien le añada una entrada «sólo para depurar».
 */
export function proxyDeApi(esPublico) {
  if (esPublico) return undefined;
  return {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  };
}

/**
 * En desarrollo, cualquier camino de la aplicación sirve `indice.html`.
 *
 * No es solo por el nombre: `PM-F05` enruta con la historia del navegador, así
 * que `/supervision` es una dirección de verdad y el servidor tiene que
 * devolver el documento para ella. Sin esto, compartir el enlace de una
 * pantalla daría un 404 — y en producción es la misma línea en el servidor
 * estático. Las cuatro rutas públicas —`/`, `/privacidad`, `/condiciones`,
 * `/investigacion`— llegan aquí por el mismo camino.
 *
 * Se excluye lo que lleva punto —`/src/principal.js`, `/favicon.svg`— porque
 * eso son archivos y sí tienen que resolverse tal cual.
 *
 * ⚠️ Y SE EXCLUYE `/api`, QUE ES EL FALLO QUE ESTE COMENTARIO EXISTE PARA
 * QUE NO SE REPITA. La primera versión reescribía todo lo que no llevara
 * punto, así que **se tragaba las peticiones al backend antes de que el proxy
 * las viera**: el navegador recibía el documento HTML donde esperaba JSON y la
 * conversación degradaba con «me quedé a medias». Costó una vuelta entera
 * encontrarlo porque el síntoma apunta al backend y la causa estaba aquí.
 *
 * En la superficie pública esa exclusión ya no decide nada: `fronteraDeApi()`
 * cerró la petición antes de llegar aquí. Se conserva porque esta pieza sirve
 * a las dos superficies y su regla no depende de cuál esté montada.
 */
function entradaEnEspanol() {
  return {
    name: 'entrada-en-espanol',
    configureServer(servidor) {
      servidor.middlewares.use((peticion, _respuesta, siguiente) => {
        const camino = (peticion.url ?? '/').split('?')[0];
        const esArchivo = camino.includes('.');
        const interno = camino.startsWith('/@') || camino.startsWith('/node_modules');
        const alBackend = esCaminoDeApi(camino);
        if (!esArchivo && !interno && !alBackend) peticion.url = '/indice.html';
        else if (camino === '/index.html') peticion.url = '/indice.html';
        siguiente();
      });
    }
  };
}

/**
 * El identificador de cliente de Google, del entorno a la página.
 *
 * Se lee `GOOGLE_CLIENT_ID` —la MISMA variable que usa el backend— en vez de
 * inventar una `VITE_…` aparte: dos nombres para el mismo dato acaban puestos
 * a medias, y el síntoma sería un botón que no abre sesión sin decir por qué.
 *
 * ⚠️ **Esto lo hornea el empaquetado, así que en producción tiene que estar
 * presente al CONSTRUIR, no al arrancar.** `Dockerfile.frontend` corre
 * `npm run construir` y hoy no recibe la variable; queda declarado en
 * `PLAN-MAESTRO.md` porque ese archivo no es de este carril.
 *
 * No es un secreto y por eso puede ir dentro de la página: identifica a la
 * aplicación ante Google, no la autoriza. Quien abra el sistema puede leerlo,
 * y así está previsto en la documentación de Google Identity Services.
 */
const CLIENTE_GOOGLE = process.env.GOOGLE_CLIENT_ID ?? '';

/**
 * El dominio institucional, para lo que la interfaz ESCRIBE.
 *
 * Misma variable que el backend —`DOMINIO_INSTITUCIONAL`— y mismo respaldo, por
 * lo mismo que `CLIENTE_GOOGLE` no inventa una `VITE_…` propia: dos nombres
 * para el mismo dato acaban puestos a medias, y aquí el síntoma sería una
 * pantalla nombrando un dominio y un servidor aceptando otro.
 *
 * ⚠️ **No es una validación.** El navegador no decide qué cuenta se admite; lo
 * decide `identidad.verificar_id_token()` con el claim `hd`. Esto sólo evita
 * que cuatro pantallas tengan `@unimayor.edu.co` escrito a mano y que un
 * despliegue de pruebas contra otro dominio de Cloud Identity quede diciendo
 * algo distinto de lo que hace.
 *
 * Lo consume `src/nucleo/configuracion/institucion.js`.
 */
const DOMINIO_INSTITUCIONAL = process.env.DOMINIO_INSTITUCIONAL ?? 'unimayor.edu.co';

/** Las direcciones que `D0` §10.1 decidió. Lo que se hornea al construir. */
const ORIGENES_DE_PRODUCCION = Object.freeze({
  publico: 'https://didaxia.pro',
  aplicacion: 'https://app.didaxia.pro'
});

/** Las dos superficies levantadas en el equipo de quien desarrolla. */
const ORIGENES_LOCALES = Object.freeze({
  publico: `http://localhost:${PUERTO_PUBLICO}`,
  aplicacion: `http://localhost:${PUERTO_APLICACION}`
});

/**
 * Los dos orígenes, **según lo que se esté haciendo**.
 *
 * `didaxia.pro` es la presencia pública y `app.didaxia.pro` la aplicación. El
 * navegador los necesita para dos cosas: decidir qué superficie monta
 * —`nucleo/configuracion/superficie.js`— y pintar los enlaces de una a otra.
 *
 * ⚠️ **AL SERVIR, LOS ENLACES APUNTAN A LAS SUPERFICIES LOCALES.** Con los
 * valores de producción horneados también en desarrollo, «Entrar al tutor» en
 * `http://localhost:5174` abría `https://app.didaxia.pro` —una dirección que
 * todavía no existe— y los enlaces legales del recorrido mandaban fuera del
 * equipo. Las dos superficies locales no se podían comprobar juntas, que era
 * justo lo que el modo público venía a permitir.
 *
 * **Un `serve` no es un despliegue y no debe hornear direcciones de
 * producción; un `build` no es un equipo de desarrollo y no debe hornear
 * `localhost`.** Por eso el respaldo lo decide el comando y no un archivo
 * `.env` que alguien tenga que recordar.
 *
 * ⚠️ **LAS VARIABLES EXPLÍCITAS MANDAN SIEMPRE**, en los dos comandos: es lo
 * que permite construir un paquete de pruebas contra otras direcciones. Se
 * comparan con `||` y no con `??` a propósito: un `ORIGEN_PUBLICO=""` en el
 * entorno no es una decisión, es una variable a medio poner, y hornear la
 * cadena vacía dejaría todos los enlaces rotos sin decir por qué.
 *
 * Esto **no toca ninguna barrera real**: la separación en producción la ejerce
 * `Caddyfile`, con un sitio por dominio y `/api/*` proxificado sólo en el de
 * la aplicación, y el backend detrás. Cambiar estos valores mueve `<a href>`,
 * no permisos.
 *
 * Mismo criterio que `CLIENTE_GOOGLE` y `DOMINIO_INSTITUCIONAL`: **lo hornea
 * el empaquetado**, así que en producción tienen que estar presentes al
 * CONSTRUIR y no al arrancar. `Dockerfile.frontend` los recibe como `ARG`.
 *
 * @param {'serve'|'build'} comando
 * @returns {{publico: string, aplicacion: string}}
 */
export function origenesPara(comando) {
  const respaldo = comando === 'serve' ? ORIGENES_LOCALES : ORIGENES_DE_PRODUCCION;
  return {
    publico: process.env.ORIGEN_PUBLICO || respaldo.publico,
    aplicacion: process.env.ORIGEN_APLICACION || respaldo.aplicacion
  };
}

/**
 * El buzón de privacidad, **vacío por defecto y a propósito**.
 *
 * `ESTADO-ACTUAL.md` §10.9 lista la definición del canal para derechos e
 * incidentes como pendiente humano, y §10.1 dice que el correo de preparación
 * no se presenta como canal institucional. Sin variable, las páginas públicas
 * escriben que el canal está pendiente de confirmación en vez de ofrecer un
 * `mailto:` vacío o una dirección que nadie aprobó. Ver
 * `src/nucleo/configuracion/contacto.js`.
 *
 * ⚠️ **EL NOMBRE EXTERNO ES `CORREO_PRIVACIDAD`**, el que el equipo ya usa y
 * documenta en `Guia-Dominios-y-Publicacion.md` y `Guia-Resend.md`. D1A había
 * llegado a inventar una variable propia para este mismo dato, y se retiró
 * antes de integrar: dos nombres para un solo buzón acaban puestos a medias, y
 * el síntoma habría sido una página diciendo «pendiente» con el correo ya
 * configurado en la otra. El nombre retirado sólo sobrevive en las dos pruebas
 * que comprueban que no vuelve.
 */
const CORREO_PRIVACIDAD = process.env.CORREO_PRIVACIDAD ?? '';

/**
 * CÓMO SE PRUEBAN LAS DOS SUPERFICIES EN LOCAL
 * ===============================================
 *
 *   npm run dev            → la APLICACIÓN en http://localhost:5173
 *   npm run dev-publico    → la PORTADA    en http://localhost:5174
 *
 * Las dos se pueden tener levantadas a la vez, y desde `D1A` se enlazan entre
 * sí: «Entrar al tutor» en la portada abre el 5173, y los documentos legales
 * del recorrido de consentimiento abren el 5174. Eso es lo que permite
 * comprobar el recorrido completo sin desplegar nada.
 *
 * Y no comparten frontera: el 5173 proxifica `/api` hacia el backend y el 5174
 * **lo cierra con un 404**, igual que hacen los dos sitios de `Caddyfile`.
 *
 * ⚠️ **`localhost` sigue siendo la aplicación por defecto.** El modo público
 * es lo ÚNICO que cambia esa elección, y sólo cuando se pide expresamente:
 * `superficieDe()` mira primero el modo forzado y sólo después el nombre de
 * servidor. Un `npm run dev` a secas se comporta exactamente igual que antes
 * de este paquete.
 *
 * En producción no hace falta ningún modo: las dos superficies salen del MISMO
 * paquete y la elige el nombre de servidor con el que se abrió. Por eso
 * `VITE_SUPERFICIE` queda en cadena vacía en cualquier modo que no sea
 * `publico` — horneado a `'publica'` en el paquete de producción, `didaxia.pro`
 * y `app.didaxia.pro` servirían los dos la portada.
 */
export default defineConfig(({ command, mode }) => {
  const esPublico = mode === MODO_PUBLICO;

  /*
   * BAJO PRUEBAS SE HORNEAN LOS ORÍGENES CANÓNICOS, Y HAY QUE DECIR POR QUÉ.
   *
   * Vitest resuelve esta configuración con `command: 'serve'`, así que sin esta
   * línea las pruebas verían `http://localhost:5173` donde afirman cosas sobre
   * `app.didaxia.pro`: `superficie-por-origen.prueba.js` comprueba qué se monta
   * en las direcciones de PRODUCCIÓN, que es donde la separación importa.
   *
   * No esconde nada, y es la diferencia con un doble de pruebas: `origenesPara()`
   * queda pura y `pruebas/contrato/configuracion-de-vite.prueba.js` la llama con
   * los dos comandos y con las variables puestas; y el respaldo local de verdad
   * se comprueba levantando el servidor en `servidores-locales.prueba.js`, donde
   * el modo ya no es `test` y esta línea no interviene.
   */
  const origenes = origenesPara(mode === MODO_PRUEBAS ? 'build' : command);

  return {
    plugins: [svelte(), fronteraPublica(esPublico), entradaEnEspanol(), presentacionIntegrada()],

    /**
     * La carpeta de estáticos se llama `publico`, no `public`.
     *
     * Vite busca `public/` por convención — el mismo problema que `ENTRADA` ya
     * resuelve para `indice.html` — y sin esto no la sirve ni la copia al
     * construir. Medido el 2026-08-20: `favicon.svg` devolvía 200 con el HTML
     * de `indice.html` en vez del archivo, por el `try_files` del servidor de
     * producción cubriendo el hueco en silencio.
     */
    publicDir: 'publico',

    define: {
      'import.meta.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(CLIENTE_GOOGLE),
      'import.meta.env.VITE_DOMINIO_INSTITUCIONAL': JSON.stringify(DOMINIO_INSTITUCIONAL),
      'import.meta.env.VITE_ORIGEN_PUBLICO': JSON.stringify(origenes.publico),
      'import.meta.env.VITE_ORIGEN_APLICACION': JSON.stringify(origenes.aplicacion),
      'import.meta.env.VITE_CORREO_PRIVACIDAD': JSON.stringify(CORREO_PRIVACIDAD),
      // Vacío salvo en el modo local público. Ver `MODO_PUBLICO` arriba.
      'import.meta.env.VITE_SUPERFICIE': JSON.stringify(esPublico ? 'publica' : '')
    },

    /**
     * Bajo pruebas se resuelve la variante de NAVEGADOR de Svelte.
     *
     * Sin esto, `import Componente from '…svelte'` trae la compilación de
     * servidor y montar falla con «`mount(...)` is not available on the server»:
     * ninguna prueba puede renderizar un componente. Es la condición que
     * `pruebas/componente/` —§12.3— necesita para existir.
     *
     * Va condicionada a `VITEST` y no puesta a secas porque `conditions`
     * gobierna también el empaquetado, y lo que sirve para probar no tiene por
     * qué servir para lo que se despliega.
     */
    resolve: process.env.VITEST ? { conditions: ['browser'] } : {},

    build: {
      rollupOptions: { input: ENTRADA }
    },

    server: {
      // Puerto propio para el modo público, para poder levantar las dos a la vez.
      port: esPublico ? PUERTO_PUBLICO : PUERTO_APLICACION,
      // Y sin proxy en la superficie pública: allí `/api` no existe.
      proxy: proxyDeApi(esPublico)
    },

    test: {
      environment: 'jsdom',
      include: ['pruebas/**/*.prueba.js'],
      globals: true
    }
  };
});
