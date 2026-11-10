import {
  HOSTNAME_APLICACION,
  ORIGEN_APLICACION,
  ORIGEN_PUBLICO
} from './origenes.js';

export const SUPERFICIE_PUBLICA = 'publica';

export const SUPERFICIE_APLICACION = 'aplicacion';

const LOCALES = Object.freeze(['localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0']);

const PRIVADAS = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

export function esHostLocal(hostname) {
  const nombre = String(hostname ?? '').toLowerCase();
  if (!nombre) return false;
  if (LOCALES.includes(nombre)) return true;
  if (nombre.endsWith('.localhost')) return true;
  return PRIVADAS.test(nombre);
}

function mismoNombre(hostname, esperado) {
  if (!esperado) return false;
  return hostname === esperado || hostname === `www.${esperado}`;
}

function origenNormalizado(origen) {
  try {
    return new URL(origen).origin.toLowerCase();
  } catch {
    return '';
  }
}

export function superficieDe({
  hostname = '',
  origin = '',
  forzada = '',
  origenAplicacion = ORIGEN_APLICACION,
  origenPublico = ORIGEN_PUBLICO
} = {}) {
  const modo = String(forzada ?? '').trim().toLowerCase();
  if (modo === SUPERFICIE_PUBLICA) return SUPERFICIE_PUBLICA;
  if (modo === SUPERFICIE_APLICACION) return SUPERFICIE_APLICACION;

  const nombre = String(hostname ?? '').toLowerCase();
  const origen = origenNormalizado(origin);

  if (origen && origen === origenNormalizado(origenPublico)) {
    return SUPERFICIE_PUBLICA;
  }
  if (origen && origen === origenNormalizado(origenAplicacion)) {
    return SUPERFICIE_APLICACION;
  }

  if (esHostLocal(nombre)) return SUPERFICIE_APLICACION;

  if (mismoNombre(nombre, HOSTNAME_APLICACION)) return SUPERFICIE_APLICACION;

  return SUPERFICIE_PUBLICA;
}

export function superficieActual(lugar = globalThis.location) {
  return superficieDe({
    hostname: lugar?.hostname ?? '',
    origin: lugar?.origin ?? '',
    forzada: import.meta.env.VITE_SUPERFICIE ?? ''
  });
}
