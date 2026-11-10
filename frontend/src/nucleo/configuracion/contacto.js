/** Canales de contacto públicos y configuración heredada del canal institucional.
 * Las direcciones del proyecto fueron proporcionadas por el equipo. La variable
 * de entorno se conserva para las superficies que usan el buzón institucional.
 */
/** El buzón aprobado, o `''` mientras no lo haya. */
export const CORREO_DE_PRIVACIDAD = import.meta.env.VITE_CORREO_PRIVACIDAD || '';

/** Canales públicos facilitados por el equipo del proyecto. */
export const CANALES_PUBLICOS = Object.freeze([
  Object.freeze({ nombre: 'Privacidad DidaxIa', correo: 'privacidad.didaxia.pro@gmail.com' }),
  Object.freeze({ nombre: 'Contacto del proyecto', correo: 'yjmunoz@didaxia.pro' })
]);

/**
 * ¿Hay un correo que se pueda ofrecer como enlace?
 *
 * Se exige la arroba y no sólo que la cadena no esté vacía: un
 * `CORREO_PRIVACIDAD=pendiente` puesto por descuido generaría
 * `mailto:pendiente`, que es un enlace roto con aspecto de funcionar. Falla
 * cerrado hacia el aviso, que es el estado honesto.
 */
export function hayCorreo() {
  return CORREO_DE_PRIVACIDAD.includes('@');
}
