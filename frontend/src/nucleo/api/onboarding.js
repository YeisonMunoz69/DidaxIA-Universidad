/**
 * El estado del recorrido y el perfil obligatorio · `EQ-020`.
 *
 * Dos rutas y una sola autoridad: `GET /api/onboarding/estado` devuelve las
 * cuatro dimensiones —perfil, consentimiento, asentimiento y representante—
 * junto al campo `acceso` ya calculado, y **es ese campo el que decide qué
 * pantalla se pinta**. El cliente no vuelve a derivarlo.
 *
 * POR QUÉ UNA LLAMADA Y NO CUATRO
 * --------------------------------
 * `rutas/consentimiento.py::estado_de_onboarding` lo dice desde el otro lado:
 * las cuatro dimensiones tienen que describir el MISMO instante. Pedirlas por
 * separado dejaría al cliente combinando un perfil de hace un segundo con un
 * consentimiento de ahora, y de esa mezcla salen pantallas que no corresponden
 * a ningún estado real del servidor.
 *
 * NOMBRE Y CORREO NO SE MANDAN, Y NO ES UN OLVIDO
 * ------------------------------------------------
 * Vienen del `id_token` de Google y ya están en `persona`. El servidor los
 * rechaza —`declarar_perfil()` no los lee— porque admitirlos dejaría que el
 * cliente reescribiera su propia identidad. Aquí ni siquiera se ofrece la
 * posibilidad de enviarlos.
 *
 * LA VINCULACIÓN A CLASE TAMPOCO VIAJA POR AQUÍ
 * -----------------------------------------------
 * La resuelve el mecanismo de clase/matrícula que ya existe (`clases.js` y la
 * pantalla `/unirse`). El estado la refleja en `perfil.clase_vinculada`; crear
 * una segunda vía habría dado dos respuestas a «¿está en una clase?».
 *
 */
import { RUTAS, pedir } from './cliente.js';

/**
 * El estado vigente completo y el `acceso` calculado.
 *
 * @returns {Promise<{
 *   acceso: string,
 *   perfil: {completo: boolean, pendientes: string[], edad: number|null,
 *            programa: string, semestre: number|null, clase_vinculada: boolean},
 *   consentimiento: {estado: string, version: string|null, al_dia: boolean},
 *   asentimiento: {estado: string, version: string|null},
 *   representante: {estado: string, limite: string|null},
 *   versiones_requeridas: {titular: string|null, asentimiento: string|null,
 *                          representante: string|null}
 * }>}
 */
export async function estado({ señal } = {}) {
  return pedir(RUTAS.onboardingEstado, { señal });
}

/**
 * Declara edad exacta, facultad, programa y semestre. Devuelve el estado ya recalculado.
 *
 * Los cuatro campos van juntos en una sola escritura porque el servidor los
 * escribe en una sola sentencia —y con la edad fija, de una vez, el plazo de
 * siete días del menor—. Mandarlos por separado habría dejado estados
 * intermedios en los que la persona es menor pero todavía no tiene plazo.
 *
 * `edad` y `semestre` viajan como número. Un `<input type="number">` entrega
 * texto y el servidor admite ambos, pero convertir aquí deja que el campo
 * vacío se distinga de un cero: `null` no se envía.
 */
export async function guardarPerfil({ edad, facultad, programa, semestre, motivo = '' }, { señal } = {}) {
  const cuerpo = {};
  const facultadNormalizada = String(facultad ?? '').trim();
  const programaNormalizado = String(programa ?? '').trim();
  if (facultadNormalizada) cuerpo.facultad = facultadNormalizada;
  if (programaNormalizado) cuerpo.programa = programaNormalizado;
  if (edad !== null && edad !== undefined && edad !== '') cuerpo.edad = Number(edad);
  if (semestre !== null && semestre !== undefined && semestre !== '') {
    cuerpo.semestre = Number(semestre);
  }
  const motivoNormalizado = String(motivo ?? '').trim();
  if (motivoNormalizado) cuerpo.motivo = motivoNormalizado;
  return pedir(RUTAS.onboardingPerfil, { metodo: 'POST', cuerpo, señal });
}
