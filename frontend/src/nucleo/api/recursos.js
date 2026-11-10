import { pedir, pedirArchivo } from './cliente.js';
import { comprobarPesoEncuesta } from '../recursos/presupuestoImagenesEncuesta.js';
const id = encodeURIComponent;
export const listar = () => pedir('/recursos');
export const clases = () => pedir('/recursos/clases');
export const docentes = () => pedir('/recursos/docentes');
export const guardarPlantilla = (r) => pedir(`/recursos/${id(r)}/plantilla`, { metodo:'POST' });
export const consultar = (r) => pedir(`/recursos/${id(r)}`);
export async function guardar(r, opciones = {}) {
 comprobarPesoEncuesta(r);
 return pedir(r.id ? `/recursos/${id(r.id)}` : '/recursos', { espera:120_000, ...opciones, metodo:r.id?'PUT':'POST', cuerpo:r });
}
export const duplicar = (r) => pedir(`/recursos/${id(r)}/duplicar`, { metodo: 'POST' });
export const publicar = (r, cursos, audiencia='estudiantes') => pedir(`/recursos/${id(r.id)}/publicar`, { metodo: 'POST', cuerpo: { clases: cursos, revision: r.revision, audiencia } });
export const cambiarEstado = (r, estado) => pedir(`/recursos/${id(r)}/estado`, { metodo: 'PATCH', cuerpo: { estado } });
export const eliminar = (r) => pedir(`/recursos/${id(r)}`, { metodo: 'DELETE' });
export async function bandeja() {
  const recursos = await pedir('/recursos/bandeja');
  if (!Array.isArray(recursos)) throw new Error('No se pudieron cargar las notificaciones de recursos. Intenta de nuevo.');
  return recursos;
}
export const abrir = (p) => pedir(`/recursos/publicaciones/${id(p)}`);
export const visitar = (p) => pedir(`/recursos/publicaciones/${id(p)}/visita`, { metodo: 'POST' });
export const actividad = (p) => pedir(`/recursos/publicaciones/${id(p)}/actividad?solo_estado=true`, { metodo:'POST' });
export const responder = (p, respuestas) => pedir(`/recursos/publicaciones/${id(p)}/respuestas`, { metodo: 'POST', cuerpo: { respuestas } });
export const metricas = (r, clase = '', envio = '') => pedir(`/recursos/${id(r)}/metricas?clase=${id(clase)}${envio?`&envio=${id(envio)}`:''}`);
export const informe = (r, clase = '', envio = '') => pedirArchivo(`/recursos/${id(r)}/informe.pdf?clase=${id(clase)}${envio?`&envio=${id(envio)}`:''}`);
export const plantillas = () => pedir('/recursos/plantillas');
export const plantilla = (p) => pedir(`/recursos/plantillas/${id(p)}`);
export const mensaje = (e) => e?.cuerpo?.detalle ?? e?.message ?? 'No se pudo completar la operación. Intenta de nuevo.';
export function encuestaNueva() {
  return { tipo: 'encuesta', titulo: 'Nueva encuesta', descripcion: '', estado: 'borrador',
    contenido: { paginas: [{ titulo: 'Primera página', descripcion: '', preguntas: [preguntaNueva()] }] } };
}
export function preguntaNueva() {
  return { id: globalThis.crypto.randomUUID(), titulo: 'Nueva pregunta', tipo: 'unica', obligatoria: true,
    ayuda: '', opciones: ['Opción 1', 'Opción 2'], minimo: 1, maximo: 5 };
}

export const ampliarCursos = (r, cursos, envio, audiencia = 'estudiantes') => pedir(`/recursos/${id(r.id)}/cursos`, { metodo:'POST', cuerpo: { clases:cursos, revision:r.revision, envio, audiencia } });

export const estudiantes = () => pedir('/recursos/estudiantes');
export const retirarDestinatarios = (r, publicaciones, envio) => pedir(`/recursos/${id(r.id)}/retirar-destinatarios`, {metodo:'POST',cuerpo:{publicaciones,envio,revision:r.revision}});
