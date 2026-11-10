import { arbolDe } from './espacios.js';

export const CAMINOS = Object.freeze({
  conversacion: '/',
  historial: '/historial',
  practica: '/practica',
  graficadora: '/graficadora',
  graficadoraProfesional: '/graficadora-profesional',
  conceptos: '/conceptos',
  biblioteca: '/biblioteca',
  datos: '/mis-datos',
  unirse: '/unirse',
  consentimiento: '/consentimiento',
  fuentes: '/fuentes',
  obras: '/obras',
  supervision: '/supervision',
  clases: '/mis-clases',
  grupo: '/grupo',
  estudiante: '/estudiante',
  conversacionesInvestigacion: '/estudiante/conversaciones',
  contexto: '/contexto',
  perfilProfesional: '/mi-perfil',
  analiticaInstitucional: '/analitica-institucional',
  consumoIA: '/consumo-ia',
  equipoInstitucional: '/equipo-institucional',
  auditoriaInstitucional: '/auditoria-institucional',
  evidencias: '/evidencias',
  solicitudesMatricula: '/solicitudes-matricula',
  recursos: '/recursos',
  encuestas: '/recursos/encuestas',
  diapositivas: '/recursos/diapositivas',
  notificaciones: '/notificaciones'
});

const ENTRADA_PROFESIONAL = Object.freeze({
  docente: CAMINOS.supervision,
  investigador: CAMINOS.evidencias
});

export function inicioDe(rol, espacio) {
  if (arbolDe(rol, espacio) === 'estudiante') return CAMINOS.conversacion;
  return ENTRADA_PROFESIONAL[rol] ?? CAMINOS.conversacion;
}
