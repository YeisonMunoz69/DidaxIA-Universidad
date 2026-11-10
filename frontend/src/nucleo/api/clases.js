/**
 * DD-12 · Clases.
 *
 * Crear clase, obtener su código, unirse con un código y listar las clases
 * propias.
 *
 * EL CODIGO DE CLASE NO ES UNA CREDENCIAL. Identifica una agrupación; no
 * autentica a nadie. Quien lo tenga puede PEDIR entrar, pero quién es cada quien
 * lo resuelve la autenticación, que va aparte. Confundir las dos cosas
 * convertiría un código compartido por WhatsApp en una puerta abierta.
 *
 * La frontera de DD-12: crear clase, unirse, listar. SIN tareas, calificaciones,
 * entregas, calendario ni mensajería. Lo que no esté en esa frase, no está.
 *
 * Y ESE «NO ESTÁ» SE COMPRUEBA LEYENDO ESTE ARCHIVO
 * --------------------------------------------------
 * El catálogo es explícito y cada operación pertenece a la gestión del grupo.
 * Si algún día aparece aquí otra que hable de entregas o de notas, la frontera se cruzó en el sitio más fácil
 * de cruzar: un módulo de red donde «solo es un endpoint más».
 *
 * `ficha()`, incorporada en Fase 7, no la cruza: devuelve lo mismo que
 * `integrantes()` ya entrega de una persona, por una ruta que además dice
 * desde qué clase se la mira. No trae progreso, ni indicios, ni conversaciones:
 * `EQ-023` reserva esa matriz a una decisión del equipo que sigue abierta.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 * Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md
 */
import { BASE, pedir, pedirArchivo } from './cliente.js';

const RUTA = '/clases';

/** Las clases propias. Del docente las suyas; del estudiante en las que está. */
export async function mias({ señal } = {}) {
  return pedir(RUTA, { señal });
}

/** Directorio alfabético paginado de matrículas en clases propias. */
export async function directorioDeEstudiantes(pagina = 1, { señal } = {}) {
  return pedir(`/grupo/estudiantes?pagina=${encodeURIComponent(pagina)}`, { señal });
}

/** Directorio alfabético institucional reservado al investigador. */
export async function directorioInstitucionalDeEstudiantes(pagina = 1, { señal, buscar = '' } = {}) {
  const filtro=buscar.trim() ? `&buscar=${encodeURIComponent(buscar.trim())}` : '';
  return pedir(`/investigacion/estudiantes?pagina=${encodeURIComponent(pagina)}${filtro}`, { señal });
}

/** Clases visibles para el selector institucional de actividad. */
export async function clasesInstitucionales({ señal } = {}) {
  const respuesta = await pedir('/investigacion/resumen', { señal });
  return respuesta?.cursos ?? [];
}

/** Crea una clase. Devuelve la clase con su código. */
export async function crear(nombre, { señal } = {}) {
  return pedir(RUTA, { metodo: 'POST', cuerpo: { nombre }, señal });
}

/** Los matriculados de una clase. */
export async function integrantes(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/integrantes`, { señal });
}

/** Cierra una matrícula vigente de una clase propia, conservando su historia. */
export async function retirarIntegrante(clase, sujeto, motivo, { señal } = {}) {
  return pedir(
    `${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}`,
    { metodo: 'DELETE', cuerpo: { motivo }, señal }
  );
}

/**
 * La ficha de UN matriculado, vista desde su clase · Fase 7.
 *
 * Existe además de `integrantes()` porque la ficha tiene que sobrevivir a
 * recargar la página: al volver de un enlace profundo no hay lista cargada de
 * la que sacar a nadie, y traerse el curso entero para mostrar a una persona
 * sería pedir de más para enseñar de menos.
 */
export async function ficha(clase, sujeto, { señal } = {}) {
  return pedir(
    `${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}`,
    { señal }
  );
}

/** Actividad e indicios auditados de un integrante, sin texto de sus chats. */
export async function analiticaDeIntegrante(clase, sujeto, { desde, hasta, señal } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  const consulta = parametros.size ? `?${parametros}` : '';
  return pedir(
    `/grupo/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}${consulta}`,
    { señal }
  );
}

/** El mismo contrato de la ficha, por el mismo borde autorizado, en PDF. */
export function pdfDeFichaIndividual(clase, sujeto, rol, { desde, hasta, señal } = {}) {
  const parametros = new URLSearchParams({ formato: 'pdf' });
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  const base = rol === 'investigador' ? '/investigacion/cursos' : '/grupo';
  return pedirArchivo(
    `${base}/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}?${parametros}`,
    { señal, espera: 60000 }
  );
}

function parametrosDeActividad({ desde, hasta, metrica, busqueda, activos } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  if (metrica) parametros.set('metrica', metrica);
  if (busqueda) parametros.set('busqueda', busqueda);
  if (activos) parametros.set('activos', '1');
  return parametros.size ? `?${parametros}` : '';
}

/** Actividad comparativa de una clase propia, sin texto ni indicadores sensibles. */
export async function actividadDeClase(clase, opciones = {}) {
  return pedir(
    `/grupo/${encodeURIComponent(clase)}/actividad${parametrosDeActividad(opciones)}`,
    { señal: opciones.señal }
  );
}

/** La misma tabla por el borde institucional auditado. */
export async function actividadInstitucionalDeClase(clase, opciones = {}) {
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/actividad${parametrosDeActividad(opciones)}`,
    { señal: opciones.señal }
  );
}

function rutaReporte(clase, rol, { desde, hasta, metricas, kpis = [], incluirIA = false }, pdf = false) {
  const base = rol === 'investigador'
    ? `/investigacion/cursos/${encodeURIComponent(clase)}`
    : `/grupo/${encodeURIComponent(clase)}`;
  const parametros = new URLSearchParams({ desde, hasta, metricas: metricas.join(',') });
  if (kpis.length) parametros.set('kpis', kpis.join(','));
  if (rol === 'investigador' && incluirIA) parametros.set('ia', '1');
  return `${base}/reporte-sesion${pdf ? '.pdf' : ''}?${parametros}`;
}

export function reporteDeSesion(clase, rol, filtros, { señal } = {}) {
  return pedir(rutaReporte(clase, rol, filtros), { señal });
}

export function pdfDeSesion(clase, rol, filtros, { señal } = {}) {
  return pedirArchivo(rutaReporte(clase, rol, filtros, true), { señal, espera: 60000 });
}

/** Corrige facultad, programa y semestre desde una clase propia. */
export async function corregirPerfil(clase, sujeto, perfil, { señal } = {}) {
  return pedir(
    `/grupo/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/perfil`,
    { metodo: 'PATCH', cuerpo: perfil, señal }
  );
}

/** URL privada del avatar de un integrante, autorizada por la clase. */
export function fotoDeIntegrante(clase, sujeto) {
  return `${BASE}${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}/foto`;
}

/** Detalle institucional de una cohorte, reservado al investigador. */
export async function claseInstitucional(clase, { desde, hasta, señal } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  const consulta = parametros.size ? `?${parametros}` : '';
  return pedir(`/investigacion/cursos/${encodeURIComponent(clase)}${consulta}`, { señal });
}

/** Ficha individual por el borde institucional auditado. */
export async function fichaInstitucional(clase, sujeto, { desde, hasta, señal } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  const consulta = parametros.size ? `?${parametros}` : '';
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}${consulta}`,
    { señal }
  );
}

/** Corrección institucional auditada del perfil académico. */
export async function corregirPerfilInstitucional(clase, sujeto, perfil, { señal } = {}) {
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/perfil`,
    { metodo: 'PATCH', cuerpo: perfil, señal }
  );
}

/** Rectificación histórica de edad, reservada al borde investigador. */
export async function rectificarEdad(clase, sujeto, edadNueva, motivo, { señal } = {}) {
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/rectificacion-edad`,
    { metodo: 'POST', cuerpo: { edad_nueva: edadNueva, motivo }, señal }
  );
}

/**
 * Regenera el código.
 *
 * **No expulsa a quien ya entró:** invalida el código, no la matrícula. Es la
 * distinción que evita que un docente vacíe su clase sin querer al rotar el
 * código porque se filtró.
 */
export async function regenerarCodigo(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/codigo`, { metodo: 'POST', señal });
}

/** Cambia únicamente el nombre visible de una clase propia. */
export async function renombrar(id, nombre, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}`, {
    metodo: 'PATCH', cuerpo: { nombre }, señal
  });
}

/** Retira la clase de las vistas y KPI; su historial sigue auditable. */
export async function archivar(id, motivo, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}`, {
    metodo: 'DELETE', cuerpo: { motivo }, señal
  });
}

/** El estudiante pide entrar con el código. Pedir, no entrar: ver la cabecera. */
export async function unirse(codigo, { señal } = {}) {
  return pedir(`${RUTA}/unirse`, { metodo: 'POST', cuerpo: { codigo }, señal });
}

/**
 * Solicitudes de matrícula visibles para la sesión.
 *
 * El servidor resuelve el alcance: el estudiante recibe las propias, el
 * docente las dirigidas a sus clases y el investigador las institucionales.
 * El cliente no envía ni inventa el rol.
 */
export async function solicitudes({ señal } = {}) {
  return pedir(`${RUTA}/solicitudes`, { señal });
}

/** Aprueba una solicitud visible; el cambio de clase ocurre en el servidor. */
export async function aprobarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/aprobar`, {
    metodo: 'POST', señal
  });
}

/** Rechaza una solicitud visible sin alterar la matrícula vigente. */
export async function rechazarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/rechazar`, {
    metodo: 'POST', señal
  });
}

/** Cancela la solicitud pendiente de la propia cuenta estudiante. */
export async function cancelarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/cancelar`, {
    metodo: 'POST', señal
  });
}
