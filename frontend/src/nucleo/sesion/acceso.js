
export const ACCESOS = Object.freeze([
  'onboarding_pendiente',
  'esperando_representante',
  'habilitado',
  'bloqueado_por_rechazo',
  'bloqueado_por_revocacion',
  'eliminacion_solicitada',
  'mantenimiento'
]);

export const SIN_CONSULTAR = 'sin_consultar';

const CON_TUTOR = Object.freeze(['habilitado']);

export function permiteTutor(acceso, tutoriaAcademicaSinInvestigacion = false) {
  return CON_TUTOR.includes(acceso) || (
    tutoriaAcademicaSinInvestigacion === true &&
    !['eliminacion_solicitada', 'mantenimiento'].includes(acceso)
  );
}

const ALCANZABLES = Object.freeze({
  onboarding_pendiente: ['/consentimiento', '/unirse', '/mis-datos'],
  esperando_representante: ['/consentimiento', '/mis-datos'],
  bloqueado_por_rechazo: ['/consentimiento', '/mis-datos'],
  bloqueado_por_revocacion: ['/consentimiento', '/mis-datos'],
  eliminacion_solicitada: ['/consentimiento', '/mis-datos'],
  mantenimiento: ['/consentimiento'],
  [SIN_CONSULTAR]: ['/consentimiento']
});

export function rutasAlcanzables(acceso, tutoriaAcademicaSinInvestigacion = false) {
  if (permiteTutor(acceso, tutoriaAcademicaSinInvestigacion)) return null;
  return ALCANZABLES[acceso] ?? ALCANZABLES[SIN_CONSULTAR];
}

export function alcanzable(camino, acceso, tutoriaAcademicaSinInvestigacion = false) {
  const permitidas = rutasAlcanzables(acceso, tutoriaAcademicaSinInvestigacion);
  return permitidas === null || permitidas.includes(camino);
}

export function destinoDe(acceso) {
  return acceso === 'eliminacion_solicitada' ? '/mis-datos' : '/consentimiento';
}

export function esBloqueo(acceso) {
  return acceso === 'bloqueado_por_rechazo' || acceso === 'bloqueado_por_revocacion';
}
