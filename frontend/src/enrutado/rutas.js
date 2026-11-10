import { CAMINOS, inicioDe } from './caminos.js';
import { ESPACIO_TUTOR, arbolDe, normalizarEspacio } from './espacios.js';
import { esEstudiante } from '../nucleo/sesion/rol.js';

export { inicioDe } from './caminos.js';

export const RUTAS = Object.freeze([
  { camino:'/recursos/docentes/encuestas',arbol:'no-estudiante',roles:['docente'],profunda:true,titulo:'Encuestas para docentes',cargar:()=>import('../docente/rutas/EncuestasParaDocentes.svelte') },
  { camino:'/recursos/docentes/diapositivas',arbol:'no-estudiante',roles:['docente'],profunda:true,titulo:'Diapositivas para docentes',cargar:()=>import('../docente/rutas/DiapositivasParaDocentes.svelte') },
  { camino: CAMINOS.notificaciones, arbol: 'estudiante', titulo: 'Notificaciones y recursos',
    icono: 'encuesta', zona: 'pie', oculta: true, roles: ['estudiante'],
    cargar: () => import('../comun/rutas/RecursosPublicados.svelte') },
  { camino: '/recursos/publicacion', arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Recurso del curso', profunda: true,
    cargar: () => import('../comun/rutas/RecursosPublicados.svelte') },
  { camino: '/notificaciones/encuestas', arbol: 'estudiante', roles: ['estudiante'], profunda: true,
    titulo: 'Encuestas del curso', cargar: () => import('../estudiante/rutas/EncuestasDelCurso.svelte') },
  { camino: '/notificaciones/diapositivas', arbol: 'estudiante', roles: ['estudiante'], profunda: true,
    titulo: 'Diapositivas del curso', cargar: () => import('../estudiante/rutas/DiapositivasDelCurso.svelte') },
  { camino: CAMINOS.conversacionesInvestigacion, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Conversaciones de estudiantes', icono: 'conversacion', profunda: true,
    cargar: () => import('../investigador/rutas/ConversacionesDeEstudiantes.svelte') },
  { camino: CAMINOS.conversacion, arbol: 'estudiante', titulo: 'Conversación', icono: 'conversacion',
    tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Conversacion.svelte') },
  { camino: CAMINOS.historial, arbol: 'estudiante', titulo: 'Mi historial', icono: 'historial',
    tutorProfesional: true,
    redirigirA: CAMINOS.conversacion, compatibilidad: true },
  { camino: CAMINOS.practica, arbol: 'estudiante', titulo: 'Práctica', icono: 'practica',
    zona: 'pie', oculta: true,
    cargar: () => import('../estudiante/rutas/Practica.svelte') },
  { camino: CAMINOS.graficadora, arbol: 'estudiante', titulo: 'Graficadora', icono: 'graficadora',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../comun/rutas/Graficadora.svelte') },
  { camino: CAMINOS.conceptos, arbol: 'estudiante', titulo: 'Conceptos', icono: 'conceptos',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Conceptos.svelte') },
  { camino: CAMINOS.biblioteca, arbol: 'estudiante', titulo: 'Biblioteca del curso', icono: 'biblioteca',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Biblioteca.svelte') },
  { camino: CAMINOS.datos, arbol: 'estudiante', titulo: 'Mis datos', icono: 'datos',
    zona: 'perfil',
    cargar: () => import('../estudiante/rutas/MisDatos.svelte') },
  { camino: CAMINOS.unirse, arbol: 'estudiante', titulo: 'Unirme a una clase', icono: 'clase',
    zona: 'pie',
    cargar: () => import('../estudiante/rutas/UnirseAClase.svelte') },
  { camino: CAMINOS.consentimiento, arbol: 'estudiante', titulo: 'Autorización', icono: 'datos',
    abierta: true,
    cargar: () => import('../estudiante/rutas/Consentimiento.svelte') },

  { camino: CAMINOS.fuentes, patron: /^\/fuentes\/[^/]+$/,
    arbol: 'estudiante', titulo: 'Material del curso', icono: 'conceptos',
    profunda: true, tutorProfesional: true, lecturaInvestigacion: true,
    cargar: () => import('../estudiante/rutas/Fuente.svelte') },
  { camino: CAMINOS.obras, patron: /^\/obras\/[^/]+$/,
    arbol: 'estudiante', titulo: 'Obra del curso', icono: 'conceptos',
    profunda: true, tutorProfesional: true, lecturaInvestigacion: true,
    cargar: () => import('../estudiante/rutas/Obra.svelte') },

  { camino: CAMINOS.clases, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Crear y gestionar clases', icono: 'clases',
    cargar: () => import('../docente/rutas/MisClases.svelte') },
  { camino: CAMINOS.graficadoraProfesional, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Graficadora', icono: 'graficadora', profunda: true,
    cargar: () => import('../comun/rutas/Graficadora.svelte') },
  { camino: CAMINOS.equipoInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Equipo institucional', icono: 'equipo-institucional',
    cargar: () => import('../investigador/rutas/EquipoInstitucional.svelte') },
  { camino: CAMINOS.analiticaInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Analítica institucional', icono: 'analitica-institucional',
    cargar: () => import('../investigador/rutas/PanelInstitucional.svelte') },
  { camino: CAMINOS.grupo, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Vista del grupo', icono: 'grupo',
    cargar: () => import('../docente/rutas/VistaDelGrupo.svelte') },
  { camino: CAMINOS.estudiante, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Estudiantes', icono: 'estudiante',
    cargar: () => import('../docente/rutas/FichaDeEstudiante.svelte') },
  { camino: CAMINOS.evidencias, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Autorizaciones de representantes', icono: 'evidencias-institucionales',
    cargar: () => import('../investigador/rutas/Evidencias.svelte') },
  { camino: CAMINOS.solicitudesMatricula, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Solicitudes de matrícula', icono: 'solicitudes',
    cargar: () => import('../investigador/rutas/SolicitudesDeClase.svelte') },
  { camino: CAMINOS.auditoriaInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Auditoría institucional', icono: 'auditoria-institucional',
    cargar: () => import('../investigador/rutas/AuditoriaInstitucional.svelte') },
  { camino: CAMINOS.consumoIA, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Consumo de IA', icono: 'consumo-ia',
    cargar: () => import('../investigador/rutas/ConsumoIA.svelte') },
  { camino: CAMINOS.supervision, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Cola de supervisión', icono: 'supervision',
    cargar: () => import('../docente/rutas/ColaDeSupervision.svelte') },
  { camino: CAMINOS.contexto, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Contexto curricular', icono: 'contexto',
    cargar: () => import('../docente/rutas/ContextoCurricular.svelte') },
  { camino: CAMINOS.recursos, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Recursos y encuestas', icono: 'recursos',
    cargar: () => import('../investigador/rutas/Recursos.svelte') },
  { camino: CAMINOS.encuestas, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Encuestas', profunda: true,
    cargar: () => import('../investigador/rutas/Encuestas.svelte') },
  { camino: CAMINOS.diapositivas, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Diapositivas', profunda: true,
    cargar: () => import('../investigador/rutas/Diapositivas.svelte') },
  { camino: CAMINOS.perfilProfesional, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Mi perfil', icono: 'perfil-institucional', zona: 'perfil',
    cargar: () => import('../comun/rutas/MiPerfilProfesional.svelte') }
]);

export function rolPermitido(ruta, rol) {
  if (!ruta?.roles) return true;
  return typeof rol === 'string' && ruta.roles.includes(rol);
}

export function puedeAbrir(ruta, rol, espacio) {
  if (!ruta) return false;
  if (ruta.lecturaInvestigacion && rol === 'investigador' && ruta.profunda) return true;
  if (ruta.arbol !== arbolDe(rol, espacio)) return false;
  return rolPermitido(ruta, rol) && esCapacidadDelEspacio(ruta, rol, espacio);
}

function esCapacidadDelEspacio(ruta, rol, espacio) {
  if (esEstudiante(rol)) return true;
  if (normalizarEspacio(espacio, rol) !== ESPACIO_TUTOR) return true;
  return Boolean(ruta.tutorProfesional);
}

export function rutaDe(camino) {
  const limpio = String(camino ?? '').split('?')[0].split('#')[0];
  return (
    RUTAS.find((r) => r.camino === limpio) ??
    RUTAS.find((r) => r.patron instanceof RegExp && r.patron.test(limpio)) ??
    null
  );
}

export function rutasDe(arbol, rol = null, espacio = null) {
  return RUTAS.filter(
    (r) =>
      r.arbol === arbol &&
      !r.abierta &&
      !r.compatibilidad &&
      !r.profunda && !r.oculta &&
      rolPermitido(r, rol) &&
      esCapacidadDelEspacio(r, rol, espacio)
  );
}

export function rutasDeZona(arbol, zona, rol = null, espacio = null) {
  return rutasDe(arbol, rol, espacio).filter((r) => (r.zona ?? 'principal') === zona);
}
