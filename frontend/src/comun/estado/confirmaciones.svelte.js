// Confirmación única para acciones explícitas. El componente raíz resuelve la
// promesa; cancelar, Esc y cerrar son equivalentes y no ejecutan la acción.
// Con alternativa optativa, la tercera decisión resuelve 'alternativa'; las
// dos decisiones habituales conservan su contrato booleano.
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
