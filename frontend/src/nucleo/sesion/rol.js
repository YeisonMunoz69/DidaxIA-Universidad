
export const ROLES = Object.freeze(['estudiante', 'docente', 'investigador']);

const NO_ESTUDIANTE = Object.freeze(['docente', 'investigador']);

export function esEstudiante(rol) {
  return !NO_ESTUDIANTE.includes(rol);
}

export function esDocente(rol) {
  return rol === 'docente';
}

export function esInvestigador(rol) {
  return rol === 'investigador';
}

export function puedeVerVectorConductual(rol) {
  return NO_ESTUDIANTE.includes(rol);
}
