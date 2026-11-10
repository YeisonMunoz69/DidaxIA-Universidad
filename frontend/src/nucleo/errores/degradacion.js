import { mensajeDe } from './mensajes.js';

export function modoDeContingencia(respuesta) {
  if (respuesta?.situacion !== 'degradado') return null;
  if (respuesta.clase === 'sin-red') return 'offline';
  if (!respuesta.clase || ['tiempo-agotado', 'servidor-caido', 'turno-interrumpido',
    'mantenimiento', 'desconocido'].includes(respuesta.clase)) return 'error_respuesta';
  return null;
}

export const CLASES = Object.freeze([
  'sin-red',
  'servidor-caido',
  'mantenimiento',
  'tiempo-agotado',
  'sin-sesion',
  'sin-permiso',
  'peticion-invalida',
  'conflicto',
  'retirada',
  'archivo-rechazado',
  'turno-interrumpido',
  'desconocido'
]);

export class FalloDeRed extends Error {
  constructor(clase, { estado = 0, causa = null, cuerpo = null } = {}) {
    super(`fallo de red (${clase})`);
    this.name = 'FalloDeRed';
    this.clase = CLASES.includes(clase) ? clase : 'desconocido';
    this.estado = estado;
    this.causa = causa;
    this.cuerpo = cuerpo;
  }

  get estadoDelServidor() {
    const valor = this.cuerpo?.estado;
    return typeof valor === 'string' ? valor : '';
  }

  get detalle() {
    const valor = this.cuerpo?.detalle;
    return typeof valor === 'string' ? valor : '';
  }
}

export function clasificarEstado(estado) {
  if (!estado) return 'sin-red';
  if (estado === 401) return 'sin-sesion';
  if (estado === 403) return 'sin-permiso';
  if (estado === 400) return 'peticion-invalida';
  if (estado === 409) return 'conflicto';
  if (estado === 410) return 'retirada';
  if (estado === 413 || estado === 415) return 'archivo-rechazado';
  if (estado === 408 || estado === 504) return 'tiempo-agotado';
  if (estado === 503) return 'mantenimiento';
  if (estado >= 500) return 'servidor-caido';
  return 'desconocido';
}

export function clasificar(error) {
  if (error instanceof FalloDeRed) return error.clase;
  if (error?.name === 'AbortError') {
    return error?.motivo === 'tiempo' ? 'tiempo-agotado' : 'desconocido';
  }
  if (error?.name === 'TypeError') return 'sin-red';
  return 'desconocido';
}

export function describir(error, ultimaFase = null) {
  const clase = clasificar(error);
  const m = mensajeDe(clase);
  return {
    situacion: 'degradado',
    clase,
    titulo: m.titulo,
    explicacion: m.detalle,
    salida: m.salida,
    ultima_fase: ultimaFase?.texto ?? '',
    reintentable: !['sin-sesion', 'sin-permiso', 'retirada'].includes(clase)
  };
}

export function sanear(respuesta) {
  if (!respuesta?.degradado) return respuesta;
  const bloques = respuesta.cuerpo?.bloques ?? [];
  return {
    ...respuesta,
    cuerpo: null,
    degradado: {
      ...respuesta.degradado,
      situacion: 'degradado',
      descartados: bloques.length
    }
  };
}
