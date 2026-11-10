/** Administración auditada del equipo institucional. */
import { pedir } from './cliente.js';

export async function listar(buscar = '', { pertenencia = 'todas', clase = '', señal } = {}) {
  const parametros = new URLSearchParams();
  if (buscar.trim()) parametros.set('buscar', buscar.trim());
  if (pertenencia !== 'todas') parametros.set('pertenencia', pertenencia);
  if (clase) parametros.set('clase', clase);
  return pedir(`/investigacion/equipo${parametros.size ? `?${parametros}` : ''}`, { señal });
}

export async function asignarRol(sujeto, rol, { señal } = {}) {
  return pedir('/gobierno/roles', {
    metodo: 'POST', cuerpo: { sujeto, rol }, señal
  });
}

export async function revocarRol(sujeto, rol, { señal } = {}) {
  return pedir('/gobierno/roles', {
    metodo: 'DELETE', cuerpo: { sujeto, rol }, señal
  });
}

export async function asignarFacultad(sujeto, facultad, { señal } = {}) {
  return pedir(`/investigacion/equipo/${encodeURIComponent(sujeto)}/facultad`, {
    metodo: 'PATCH', cuerpo: { facultad }, señal
  });
}

export function fotoDePersona(sujeto) {
  return `/api/investigacion/equipo/${encodeURIComponent(sujeto)}/foto`;
}

export async function listarInvitaciones({ señal } = {}) {
  return pedir('/gobierno/invitaciones', { señal });
}

export async function invitar(correo, rol, { señal } = {}) {
  return pedir('/gobierno/invitaciones', {
    metodo: 'POST', cuerpo: { correo, rol }, señal
  });
}

export async function revocarInvitacion(secuencia, { señal } = {}) {
  return pedir(`/gobierno/invitaciones/${encodeURIComponent(secuencia)}`, {
    metodo: 'DELETE', señal
  });
}
