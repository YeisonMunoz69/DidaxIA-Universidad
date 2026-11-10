import { RUTAS, pedir } from './cliente.js';

export async function consultar({ señal } = {}) {
  return pedir(RUTAS.sesion, { señal });
}

export async function iniciarConGoogle(idToken, { señal } = {}) {
  const invitacion = typeof location === 'undefined'
    ? ''
    : new URLSearchParams(location.search).get('invitacion') ?? '';
  return pedir(RUTAS.sesionGoogle, {
    metodo: 'POST',
    cuerpo: { id_token: idToken, ...(invitacion ? { invitacion } : {}) },
    señal
  }).then((respuesta) => {
    if (invitacion && typeof history !== 'undefined') {
      const url = new URL(location.href);
      url.searchParams.delete('invitacion');
      history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
    }
    return respuesta;
  });
}

export async function cerrar({ señal } = {}) {
  return pedir(RUTAS.sesion, { metodo: 'DELETE', señal });
}

export async function tiempoRestante({ señal } = {}) {
  return pedir(RUTAS.renovar, { metodo: 'POST', señal });
}

export async function reautenticar(idToken, { señal } = {}) {
  return pedir(RUTAS.reautenticar, {
    metodo: 'POST',
    cuerpo: { id_token: idToken },
    señal
  });
}

export async function reiniciar({ señal } = {}) {
  return pedir(RUTAS.reiniciarSesion, { metodo: 'POST', señal });
}
