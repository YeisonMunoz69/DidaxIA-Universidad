const FENOMENOS = new Set(['conductual.ansiedad_matematica',
  'aprendizaje.concepciones_dos_niveles', 'conductual.reiteracion_tras_correccion',
  'conductual.hibrido_ps_anx', 'aprendizaje.preconcepciones_dialogo', 'conductual.hibrido_reiteracion']);

export function esFenomenoAnteproyecto(indicador) {
  return FENOMENOS.has(indicador?.codigo);
}

export function esEvidenciaDeDialogo(indicador) {
  return esFenomenoAnteproyecto(indicador) || Boolean(indicador?.codigo?.startsWith('conductual.observable_'));
}

export function tieneValorPublicable(indicador) {
  return indicador?.estado === 'disponible' && Number.isFinite(indicador.valor);
}

export function visibleEnTablero(indicador) {
  return tieneValorPublicable(indicador) || (esEvidenciaDeDialogo(indicador)
    && ['sin_datos', 'muestra_insuficiente', 'datos_incompletos'].includes(indicador.estado));
}

const PARES_FACTORES = [
  ['conductual.hibrido_ps_anx', 'conductual.ansiedad_matematica', 'tension'],
  ['aprendizaje.preconcepciones_dialogo', 'aprendizaje.concepciones_dos_niveles', 'concepciones'],
  ['conductual.hibrido_reiteracion', 'conductual.reiteracion_tras_correccion', 'reiteracion']
];

export function factorPrincipal(indicador, conjunto = []) {
  const par = PARES_FACTORES.find(([hibrido, original]) => [hibrido, original].includes(indicador?.codigo));
  if (!par) return '';
  const elegido = conjunto.some(item => item.codigo === par[0]) ? par[0] : par[1];
  return indicador.codigo === elegido ? par[2] : '';
}

export function ordenarFactores(indicadores) {
  return [...indicadores.filter(item => factorPrincipal(item, indicadores)),
    ...indicadores.filter(item => !factorPrincipal(item, indicadores))];
}
