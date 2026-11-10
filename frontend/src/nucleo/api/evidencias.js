import { RUTAS, pedir, pedirArchivo } from './cliente.js';

export const FILTROS = Object.freeze(['pendiente', 'aprobada', 'rechazada', 'todos']);

export const FILTRO_POR_DEFECTO = 'pendiente';

export const TAMANO_PAGINA = 20;

function caminoDe(evidencia) {
  return `${RUTAS.evidencias}/${Number(evidencia)}`;
}

export async function listar({
  estado = FILTRO_POR_DEFECTO,
  limite = TAMANO_PAGINA,
  cursor = null,
  señal
} = {}) {
  const parametros = new URLSearchParams();
  if (estado) parametros.set('estado', estado);
  if (limite) parametros.set('limite', String(limite));
  if (cursor) parametros.set('cursor', cursor);

  const respuesta = await pedir(`${RUTAS.evidencias}?${parametros}`, { señal });
  return {
    evidencias: respuesta?.evidencias ?? [],
    cursorSiguiente: respuesta?.cursor_siguiente ?? null,
    hayMas: Boolean(respuesta?.hay_mas),
    filtro: respuesta?.filtro ?? estado,
    limite: respuesta?.limite ?? limite
  };
}

export async function detalle(evidencia, { señal } = {}) {
  const documento = await pedir(caminoDe(evidencia), { señal });
  return { ...documento, motivo: documento?.motivo ?? '' };
}

export async function archivo(evidencia, { señal } = {}) {
  return pedirArchivo(`${caminoDe(evidencia)}/archivo`, { señal });
}

export async function aprobar(evidencia, { señal } = {}) {
  return pedir(`${RUTAS.evidencia}/${Number(evidencia)}/revisar`, {
    metodo: 'POST',
    cuerpo: { resultado: 'aprobada' },
    señal
  });
}

export async function rechazar(evidencia, motivo, { señal } = {}) {
  const texto = String(motivo ?? '').trim();
  if (!texto) throw new Error('un rechazo exige un motivo comprensible');
  return pedir(`${RUTAS.evidencia}/${Number(evidencia)}/revisar`, {
    metodo: 'POST',
    cuerpo: { resultado: 'rechazada', motivo: texto },
    señal
  });
}
