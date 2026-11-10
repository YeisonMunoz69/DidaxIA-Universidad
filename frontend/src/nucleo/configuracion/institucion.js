/**
 * El dominio institucional, para lo que se ESCRIBE en pantalla.
 *
 * El backend ya lee `DOMINIO_INSTITUCIONAL` —con `unimayor.edu.co` por
 * defecto— y es él quien comprueba el claim `hd` del `id_token`. El frontend
 * tenía el mismo dominio escrito a mano en cuatro pantallas, así que un
 * despliegue de pruebas contra otro dominio de Cloud Identity aceptaba cuentas
 * que la interfaz seguía diciendo que no aceptaba.
 *
 * ⚠️ ESTO NO VALIDA NADA, Y NO PUEDE HACERLO
 * --------------------------------------------
 * Es presentación. Comprobar el dominio en el navegador no es una barrera:
 * quien abra las herramientas lo cambia. La autoridad sobre `hd` sigue siendo
 * del servidor —`identidad.verificar_id_token()`— y esta constante no
 * interviene en ninguna decisión de acceso, ni en una guarda, ni en un cuerpo
 * enviado. Sólo aparece dentro de frases.
 *
 * DE DÓNDE SALE EL VALOR
 * -----------------------
 * `vite.config.js` lee `process.env.DOMINIO_INSTITUCIONAL` —la MISMA variable
 * del backend, no una `VITE_…` inventada aparte— y la hornea como
 * `import.meta.env.VITE_DOMINIO_INSTITUCIONAL`. Dos nombres para el mismo dato
 * acaban puestos a medias, y el síntoma sería una pantalla nombrando un
 * dominio y un servidor aceptando otro.
 *
 * Como lo hornea el empaquetado, tiene que estar presente al **construir**, no
 * al arrancar — igual que `GOOGLE_CLIENT_ID`, y por la misma razón.
 *
 * El respaldo es `unimayor.edu.co`: sin variable, la interfaz dice lo que este
 * proyecto dice hoy, no una cadena vacía ni un hueco.
 *
 */

/** El dominio sin arroba: `unimayor.edu.co`. */
export const DOMINIO_INSTITUCIONAL =
  import.meta.env.VITE_DOMINIO_INSTITUCIONAL || 'unimayor.edu.co';

/**
 * El dominio ya con arroba, como se escribe dentro de una frase.
 *
 * Se deriva aquí y no en cada pantalla porque las cuatro que lo nombran
 * escribían la arroba a mano, y una de ellas podía olvidarla sin que nada lo
 * dijera.
 */
export const CORREO_INSTITUCIONAL = `@${DOMINIO_INSTITUCIONAL}`;
