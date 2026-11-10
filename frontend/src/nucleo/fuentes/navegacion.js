import { CAMINOS, inicioDe } from '../../enrutado/caminos.js';

const ANCLA = /^[A-Za-z0-9_-]{1,64}$/;

export const PARAMETRO_DE_RETORNO = 'volver';

export function esCaminoInterno(camino) {
  if (typeof camino !== 'string' || !camino.startsWith('/')) return false;
  if (camino.startsWith('//')) return false;
  if (camino.includes('\\')) return false;

  const [base, ancla] = camino.split('#', 2);
  if (ancla !== undefined && !ANCLA.test(ancla)) return false;
  if (base.includes('?')) return false;

  return Object.values(CAMINOS).includes(base);
}

export function destinoDeRetorno(pedido, rol = 'estudiante') {
  return esCaminoInterno(pedido) ? pedido : inicioDe(rol);
}

export function caminoDeFuente(id, volverA) {
  const base = `/fuentes/${encodeURIComponent(id)}`;
  if (!esCaminoInterno(volverA)) return base;
  return `${base}?${PARAMETRO_DE_RETORNO}=${encodeURIComponent(volverA)}`;
}

export function caminoDeObra(clave, { parte, fragmento, volverA, vista } = {}) {
  const parametros = new URLSearchParams();
  if (parte) parametros.set('parte', parte);
  if (fragmento) parametros.set('fragmento', fragmento);
  if (vista === 'original') parametros.set('vista', 'original');
  if (esCaminoInterno(volverA)) parametros.set(PARAMETRO_DE_RETORNO, volverA);
  const consulta = parametros.toString();
  return `/obras/${encodeURIComponent(clave)}${consulta ? `?${consulta}` : ''}`;
}

export function fragmentoDelCamino(camino) {
  const partes = String(camino ?? '').split('?')[0].split('/');
  return partes[1] === 'fuentes' && partes[2] ? decodeURIComponent(partes[2]) : '';
}

export function obraDelCamino(camino) {
  const partes = String(camino ?? '').split('?')[0].split('/');
  return partes[1] === 'obras' && partes[2] ? decodeURIComponent(partes[2]) : '';
}
