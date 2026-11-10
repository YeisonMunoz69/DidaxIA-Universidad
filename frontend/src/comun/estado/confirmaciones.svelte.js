let solicitud = $state(null);
let resolverActual = null;

export function confirmarAccion(datos) {
  if (resolverActual) return Promise.resolve(false);
  return new Promise((resolver) => {
    resolverActual = resolver;
    solicitud = { tipo:'confirmar', confirmar:'Confirmar', cancelar:'Volver', ...datos };
  });
}

export const confirmaciones = {
  get solicitud() { return solicitud; },
  responder(aceptada) {
    const resolver = resolverActual;
    resolverActual = null;
    solicitud = null;
    resolver?.(aceptada);
  }
};
