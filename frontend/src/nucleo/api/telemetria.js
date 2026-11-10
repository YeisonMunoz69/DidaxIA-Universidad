/**
 * Emisor mínimo de hechos que sólo observa la interfaz.
 *
 * La clave vive en memoria durante el intento y se reutiliza si la petición se
 * repite. No se usa `localStorage`: la telemetría no deja una segunda bitácora
 * en el navegador. Tampoco viajan sujeto, rol, correo, nombre ni texto de la
 * conversación; esas autoridades pertenecen al servidor y al historial.
 */
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

/** Un identificador corto de la definición, sin enviar la expresión. */
export function identificadorDeGrafica(definicion) {
  const texto = String(definicion ?? '');
  let resumen = 2166136261;
  for (let i = 0; i < texto.length; i += 1) {
    resumen ^= texto.charCodeAt(i);
    resumen = Math.imul(resumen, 16777619);
  }
  return `grafica-${(resumen >>> 0).toString(16).padStart(8, '0')}`;
}

/**
 * Registra un hecho y conserva la misma clave en un reintento de transporte.
 * Quien necesite conocer el fallo puede esperar esta promesa.
 */
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

/**
 * Para acciones que no deben romperse si la medición no está disponible.
 * Devuelve `false` en vez de dejar una promesa rechazada sin observar.
 */
export async function emitirEvento(tipo, referencias = {}, opciones = {}) {
  try {
    await registrarEvento(tipo, referencias, opciones);
    return true;
  } catch {
    return false;
  }
}
