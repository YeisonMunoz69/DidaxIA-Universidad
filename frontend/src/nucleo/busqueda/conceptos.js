export function normalizar(texto = '') {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es')
    .trim();
}

export function coincideConConsulta(concepto, consulta) {
  const palabras = normalizar(consulta).split(/\s+/).filter(Boolean);
  if (!palabras.length) return true;

  const vocabulario = [normalizar(concepto.nombre), ...(concepto.terminos_busqueda ?? [])]
    .map(normalizar);
  return palabras.every((palabra) =>
    vocabulario.some((termino) => termino.includes(palabra))
  );
}
