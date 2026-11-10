/**
 * Caminos canónicos y destinos iniciales de DidaxIa.
 *
 * Este módulo contiene sólo datos: no carga pantallas ni componentes. Por eso
 * puede ser usado por la navegación del lector de fuentes sin formar el ciclo
 * `rutas -> Conversacion -> MaterialDelCurso -> rutas`.
 *
 */
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

/**
 * La entrada del espacio PROFESIONAL de cada rol.
 *
 * ⚠️ Sólo del profesional. La entrada del espacio Tutor es la conversación para
 * todo el mundo —`EQ-031` concede las mismas capacidades de consulta, y la
 * conversación es por donde se entra a ellas—, así que no se repite aquí: una
 * segunda fila `docente → /` habría creado dos respuestas para la misma
 * pregunta según qué espacio esté activo.
 */
const ENTRADA_PROFESIONAL = Object.freeze({
  docente: CAMINOS.supervision,
  investigador: CAMINOS.evidencias
});

/**
 * El inicio seguro de un rol en un espacio, sin importar el árbol de componentes.
 *
 * ⚠️ **Sin `espacio` responde exactamente lo de antes de `EQ-031`**, porque
 * `arbolDe()` cae al predeterminado del rol: estudiante a `/`, docente a
 * `/supervision`, investigador a `/evidencias`, y cualquier rol desconocido a
 * `/` — que es el fallo seguro de `esEstudiante()` heredado tal cual.
 *
 * `ENTRADA_PROFESIONAL` no se expone. Un mapa exportado invita a
 * `ENTRADA[algo]`, y `algo` acabó siendo un árbol la última vez (C2B): con dos
 * árboles y tres roles, `INICIO['no-estudiante']` mandaba a una investigadora a
 * `/supervision`. Se lee **sólo** con esta función.
 */
export function inicioDe(rol, espacio) {
  if (arbolDe(rol, espacio) === 'estudiante') return CAMINOS.conversacion;
  return ENTRADA_PROFESIONAL[rol] ?? CAMINOS.conversacion;
}
