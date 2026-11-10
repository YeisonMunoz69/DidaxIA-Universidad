export const CORREO_DE_PRIVACIDAD = import.meta.env.VITE_CORREO_PRIVACIDAD || '';

export const CANALES_PUBLICOS = Object.freeze([
  Object.freeze({ nombre: 'Privacidad DidaxIa', correo: 'privacidad.didaxia.pro@gmail.com' }),
  Object.freeze({ nombre: 'Contacto del proyecto', correo: 'yjmunoz@didaxia.pro' })
]);

export function hayCorreo() {
  return CORREO_DE_PRIVACIDAD.includes('@');
}
