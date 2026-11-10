
export const NOTACIONES = Object.freeze({
  operador: { nombre: 'Operador', ejemplo: 'd/dx [ f(x) ]' },
  euler: { nombre: 'Operador de Euler', ejemplo: 'D_x [ f(x) ]' },
  lagrange: { nombre: 'Lagrange', ejemplo: "f'(x)" },
  leibniz: { nombre: 'Leibniz', ejemplo: 'dy/dx' }
});

export const ADMITIDAS = Object.freeze(Object.keys(NOTACIONES));

export const POR_DEFECTO = 'operador';

export function admitida(id) {
  return typeof id === 'string' && Object.hasOwn(NOTACIONES, id);
}

export function paraEnviar(id) {
  return admitida(id) ? id : '';
}
