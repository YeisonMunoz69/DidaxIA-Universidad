
export const ORIGEN_PUBLICO =
  import.meta.env.VITE_ORIGEN_PUBLICO || 'https://didaxia.pro';

export const ORIGEN_APLICACION =
  import.meta.env.VITE_ORIGEN_APLICACION || 'https://app.didaxia.pro';

export function hostnameDe(origen) {
  try {
    return new URL(origen).hostname.toLowerCase();
  } catch {
    return '';
  }
}

export const HOSTNAME_PUBLICO = hostnameDe(ORIGEN_PUBLICO);

export const HOSTNAME_APLICACION = hostnameDe(ORIGEN_APLICACION);

export const PAGINAS_PUBLICAS = Object.freeze([
  Object.freeze({
    camino: '/',
    titulo: 'Inicio',
    resumen: 'Qué es DidaxIa, quién lo hace y para qué sirve.'
  }),
  Object.freeze({
    camino: '/privacidad',
    titulo: 'Privacidad',
    documento: true,
    resumen: 'Qué datos se prevén, para qué, quién los ve y qué derechos hay.'
  }),
  Object.freeze({
    camino: '/condiciones',
    titulo: 'Condiciones',
    documento: true,
    resumen: 'Cómo se accede, qué alcance tiene el tutor y qué se espera de quien lo usa.'
  }),
  Object.freeze({
    camino: '/investigacion',
    titulo: 'Investigación',
    documento: true,
    resumen: 'El objetivo del proyecto, el piloto y qué se publica de él.'
  })
]);

export const DOCUMENTOS_PUBLICOS = Object.freeze(
  PAGINAS_PUBLICAS.filter((p) => p.documento)
);

export function enlacePublico(camino) {
  return `${ORIGEN_PUBLICO}${camino === '/' ? '' : camino}`;
}

export const ENLACE_AL_TUTOR = ORIGEN_APLICACION;
