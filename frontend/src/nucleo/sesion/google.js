
export const GUION = 'https://accounts.google.com/gsi/client';

export function guionListo() {
  return Boolean(globalThis.google?.accounts?.id);
}

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
