
export const FECHA_ILEGIBLE = 'fecha no disponible';

export function fechaLegible(valor) {
  if (!valor) return FECHA_ILEGIBLE;
  try {
    const fecha = valor instanceof Date ? valor : new Date(valor);
    if (Number.isNaN(fecha.getTime())) return FECHA_ILEGIBLE;
    return fecha.toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
  } catch {
    return FECHA_ILEGIBLE;
  }
}
