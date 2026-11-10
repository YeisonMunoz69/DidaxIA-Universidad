import { pedir, pedirArchivo } from './cliente.js';

export async function listar({
  pagina = 1, operacion = '', actor = '', sujeto = '', desde = '', hasta = '',
  categoria = '', dobleAprobacion = '', señal
} = {}) {
  const parametros = new URLSearchParams({ pagina: String(pagina) });
  if (operacion.trim()) parametros.set('operacion', operacion.trim());
  if (actor.trim()) parametros.set('actor', actor.trim());
  if (sujeto.trim()) parametros.set('sujeto', sujeto.trim());
  if (desde) parametros.set('desde', desde);
  if (hasta) parametros.set('hasta', hasta);
  if (categoria) parametros.set('categoria', categoria);
  if (dobleAprobacion) parametros.set('doble_aprobacion', dobleAprobacion);
  return pedir(`/investigacion/auditoria?${parametros}`, { señal });
}

export async function descargarInforme(filtros, { confirmado = false, señal } = {}) {
  return pedirArchivo('/investigacion/auditoria/informe', {
    metodo: 'POST', cuerpo: { filtros, confirmado }, señal
  });
}
