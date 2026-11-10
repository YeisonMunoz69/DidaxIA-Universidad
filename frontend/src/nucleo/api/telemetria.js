import { pedir } from './cliente.js';

const RUTA = '/telemetria/eventos';
const PATRON_REFERENCIA = /^[A-Za-z0-9:._~-]{1,128}$/;
let secuencia = 0;

function claveNueva() {
  const uuid = globalThis.crypto?.randomUUID?.();
  if (uuid) return `interfaz:${uuid}`;
  secuencia += 1;
  return `interfaz:${Date.now().toString(36)}:${secuencia.toString(36)}`;
}

function referencia(valor) {
  const limpia = typeof valor === 'string' ? valor.trim() : '';
  return PATRON_REFERENCIA.test(limpia) ? limpia : undefined;
}

function sePuedeReintentar(error) {
  const estado = Number(error?.estado ?? 0);
  return estado === 0 || estado === 408 || estado === 429 || estado >= 500;
}

export function identificadorDeGrafica(definicion) {
  const texto = String(definicion ?? '');
  let resumen = 2166136261;
  for (let i = 0; i < texto.length; i += 1) {
    resumen ^= texto.charCodeAt(i);
    resumen = Math.imul(resumen, 16777619);
  }
  return `grafica-${(resumen >>> 0).toString(16).padStart(8, '0')}`;
}

export async function registrarEvento(
  tipo,
  { clase, conversacion, turno, concepto, metadatos = {}, ocurridoEn } = {},
  { claveIdempotencia = claveNueva(), reintentos = 1 } = {},
) {
  const cuerpo = {
    tipo,
    clave_idempotencia: claveIdempotencia,
    ocurrido_en: ocurridoEn ?? new Date().toISOString(),
    metadatos: { ...metadatos },
  };
  for (const [clave, valor] of Object.entries({ clase, conversacion, turno, concepto })) {
    const valida = referencia(valor);
    if (valida) cuerpo[clave] = valida;
  }

  let ultimoFallo;
  for (let intento = 0; intento <= reintentos; intento += 1) {
    try {
      return await pedir(RUTA, { metodo: 'POST', cuerpo });
    } catch (error) {
      ultimoFallo = error;
      if (!sePuedeReintentar(error)) throw error;
    }
  }
  throw ultimoFallo;
}

export async function emitirEvento(tipo, referencias = {}, opciones = {}) {
  try {
    await registrarEvento(tipo, referencias, opciones);
    return true;
  } catch {
    return false;
  }
}
