const PATRON_INTERNO = /^(?:C-[A-Z0-9-]+|[NFM]-?\d+)$/i;

/** Distingue un rótulo legible de una clave útil sólo para el sistema. */
export function esNombreHumano(valor) {
  const texto = typeof valor === 'string' ? valor.trim() : '';
  return Boolean(texto) && !PATRON_INTERNO.test(texto);
}
