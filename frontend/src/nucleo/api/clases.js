import { BASE, pedir, pedirArchivo } from './cliente.js';

const RUTA = '/clases';

export async function mias({ señal } = {}) {
  return pedir(RUTA, { señal });
}

export async function directorioDeEstudiantes(pagina = 1, { señal } = {}) {
  return pedir(`/grupo/estudiantes?pagina=${encodeURIComponent(pagina)}`, { señal });
}

export async function directorioInstitucionalDeEstudiantes(pagina = 1, { señal, buscar = '' } = {}) {
  const filtro=buscar.trim() ? `&buscar=${encodeURIComponent(buscar.trim())}` : '';
  return pedir(`/investigacion/estudiantes?pagina=${encodeURIComponent(pagina)}${filtro}`, { señal });
}

export async function clasesInstitucionales({ señal } = {}) {
  const respuesta = await pedir('/investigacion/resumen', { señal });
  return respuesta?.cursos ?? [];
}

export async function crear(nombre, { señal } = {}) {
  return pedir(RUTA, { metodo: 'POST', cuerpo: { nombre }, señal });
}

export async function integrantes(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/integrantes`, { señal });
}

export async function retirarIntegrante(clase, sujeto, motivo, { señal } = {}) {
  return pedir(
    `${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}`,
    { metodo: 'DELETE', cuerpo: { motivo }, señal }
  );
}

export async function ficha(clase, sujeto, { señal } = {}) {
  return pedir(
    `${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}`,
    { señal }
  );
}

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

export async function actividadDeClase(clase, opciones = {}) {
  return pedir(
    `/grupo/${encodeURIComponent(clase)}/actividad${parametrosDeActividad(opciones)}`,
    { señal: opciones.señal }
  );
}

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

export async function corregirPerfil(clase, sujeto, perfil, { señal } = {}) {
  return pedir(
    `/grupo/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/perfil`,
    { metodo: 'PATCH', cuerpo: perfil, señal }
  );
}

export function fotoDeIntegrante(clase, sujeto) {
  return `${BASE}${RUTA}/${encodeURIComponent(clase)}/integrantes/${encodeURIComponent(sujeto)}/foto`;
}

export async function claseInstitucional(clase, { desde, hasta, señal } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  const consulta = parametros.size ? `?${parametros}` : '';
  return pedir(`/investigacion/cursos/${encodeURIComponent(clase)}${consulta}`, { señal });
}

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

export async function corregirPerfilInstitucional(clase, sujeto, perfil, { señal } = {}) {
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/perfil`,
    { metodo: 'PATCH', cuerpo: perfil, señal }
  );
}

export async function rectificarEdad(clase, sujeto, edadNueva, motivo, { señal } = {}) {
  return pedir(
    `/investigacion/cursos/${encodeURIComponent(clase)}/estudiantes/${encodeURIComponent(sujeto)}/rectificacion-edad`,
    { metodo: 'POST', cuerpo: { edad_nueva: edadNueva, motivo }, señal }
  );
}

export async function regenerarCodigo(id, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}/codigo`, { metodo: 'POST', señal });
}

export async function renombrar(id, nombre, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}`, {
    metodo: 'PATCH', cuerpo: { nombre }, señal
  });
}

export async function archivar(id, motivo, { señal } = {}) {
  return pedir(`${RUTA}/${encodeURIComponent(id)}`, {
    metodo: 'DELETE', cuerpo: { motivo }, señal
  });
}

export async function unirse(codigo, { señal } = {}) {
  return pedir(`${RUTA}/unirse`, { metodo: 'POST', cuerpo: { codigo }, señal });
}

export async function solicitudes({ señal } = {}) {
  return pedir(`${RUTA}/solicitudes`, { señal });
}

export async function aprobarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/aprobar`, {
    metodo: 'POST', señal
  });
}

export async function rechazarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/rechazar`, {
    metodo: 'POST', señal
  });
}

export async function cancelarSolicitud(id, { señal } = {}) {
  return pedir(`${RUTA}/solicitudes/${encodeURIComponent(id)}/cancelar`, {
    metodo: 'POST', señal
  });
}
