/**
 * Cargar el guion de Google Identity Services, una sola vez.
 *
 * Lo necesitan **dos** componentes con propósitos distintos: entrar
 * (`EntrarConGoogle.svelte`) y reautenticarse (`ReautenticarConGoogle.svelte`).
 * Son dos cosas distintas —`POST /api/sesion/google` acepta cualquier token
 * válido, `POST /api/sesion/reautenticar` exige que Google lo haya firmado hace
 * un momento— pero comparten exactamente este trozo: meter el `<script>` en la
 * página y saber cuándo está listo.
 *
 * Duplicarlo habría metido dos veces la misma etiqueta en el documento, y la
 * segunda copia habría reinicializado el cliente de Google por debajo del botón
 * que ya estaba pintado.
 *
 * AQUÍ NO SE GUARDA NINGÚN TOKEN
 * -------------------------------
 * Este módulo carga un guion y nada más. La credencial que Google entrega va
 * directa a la función que la pidió, se manda al servidor y se olvida:
 * conservarla serían dos credenciales vivas donde basta la cookie que el
 * servidor acaba de poner.
 *
 */

/** De dónde sale el guion oficial. Un solo sitio donde cambiarlo. */
export const GUION = 'https://accounts.google.com/gsi/client';

/** Si el objeto de Google ya está disponible en la página. */
export function guionListo() {
  return Boolean(globalThis.google?.accounts?.id);
}

/**
 * Carga el guion, o resuelve enseguida si ya estaba.
 *
 * No lanza cuando no hay `document` —una prueba de nodo sin DOM— porque quien
 * llama comprueba después `guionListo()`: distinguir «no hay navegador» de «no
 * cargó» no le sirve a nadie y obligaría a cada llamador a tratar dos fallos.
 *
 * Un guion que **carga pero llega incompleto** no se da por bueno: es el 200
 * mentiroso que un proxy corporativo puede devolver, y quien llama lo detecta
 * comprobando `guionListo()` después de esperar.
 */
export function cargarGuion() {
  if (guionListo()) return Promise.resolve();
  if (typeof document === 'undefined') return Promise.resolve();

  const yaEsta = document.querySelector(`script[src="${GUION}"]`);
  if (yaEsta) {
    return new Promise((ok, mal) => {
      yaEsta.addEventListener('load', ok, { once: true });
      yaEsta.addEventListener('error', mal, { once: true });
    });
  }

  return new Promise((ok, mal) => {
    const etiqueta = document.createElement('script');
    etiqueta.src = GUION;
    etiqueta.async = true;
    etiqueta.onload = ok;
    etiqueta.onerror = () => mal(new Error('no se pudo cargar el guion de Google'));
    document.head.appendChild(etiqueta);
  });
}

/**
 * Pinta el botón oficial de Google dentro de `hueco`.
 *
 * `callback` recibe la respuesta de Google —con `credential`— y decide qué
 * hacer con ella. Este módulo no la mira.
 *
 * `auto_select: false` siempre: reautenticarse con una cuenta elegida
 * automáticamente sería justo lo contrario de exigir que la persona esté
 * delante ahora.
 */
export function pintarBoton(hueco, { cliente, callback, tema, ancho, texto = 'signin_with' }) {
  if (!hueco || !guionListo()) return;
  hueco.innerHTML = '';
  globalThis.google.accounts.id.initialize({
    client_id: cliente,
    callback,
    auto_select: false,
    cancel_on_tap_outside: true
  });
  globalThis.google.accounts.id.renderButton(hueco, {
    type: 'standard',
    theme: tema,
    size: 'large',
    text: texto,
    shape: 'rectangular',
    width: ancho,
    locale: 'es'
  });
}
