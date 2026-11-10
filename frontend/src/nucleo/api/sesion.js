/**
 * Sesión y rol.
 *
 * Entrada institucional, cierre, reautenticación y consulta del rol vigente.
 * El rol lo dice el servidor; el cliente no lo deduce.
 *
 * UNA SOLA PUERTA, Y NINGUNA ANÓNIMA · `EQ-020`
 * -----------------------------------------------
 * `POST /api/sesion` —la vía anónima— responde **401** desde el hito B1 y este
 * módulo ya no la ofrece: `iniciar()` se retiró. La única forma de abrir sesión
 * es `iniciarConGoogle()`, y el rol lo decide el servidor con su registro de
 * docentes. Conservar una función que llamara a la vía retirada habría dejado a
 * mano el gesto que el backend cerró.
 *
 * POR QUÉ NO HAY AQUÍ NINGÚN «RECORDAR SESIÓN»
 * ---------------------------------------------
 * La sesión viaja en cookie y la pone el servidor. Guardar una copia del
 * identificador —o peor, de un testigo— en `localStorage` lo dejaría legible
 * por cualquier guion de la página y sobreviviría al cierre del navegador.
 * `credentials: 'include'` en `cliente.js` es todo lo que hace falta.
 *
 * EL ROL SE PREGUNTA, NO SE INFIERE
 * ----------------------------------
 * `07-Estructura-del-Frontend.md` §11: las guardas del cliente son cortesía y
 * la negativa efectiva la ejerce el servidor. Si el cliente dedujera el rol de
 * algo que ya tiene a mano, bastaría cambiarlo en las herramientas del
 * navegador para ver enlaces que no le tocan — enlaces, no datos, pero el
 * proyecto tiene una razón fuerte para no acostumbrarse a eso.
 *
 */
import { RUTAS, pedir } from './cliente.js';

/**
 * Quién es y qué rol tiene, según el servidor.
 *
 * ⚠️ **Esta consulta YA NO CREA NADA.** Hasta el hito B1 `GET /api/sesion`
 * abría una sesión anónima al consultarla; `EQ-020` lo prohíbe con todas las
 * letras y hoy responde **401** a quien llegue sin cookie válida. Ese 401 es el
 * estado normal de quien acaba de llegar —no una avería, no una sesión
 * caducada— y `degradacion.js` lo clasifica como `sin-sesion` justamente para
 * que nadie lo pinte como caída del sistema.
 *
 * @returns {Promise<{rol: string, correo: string|null, nombre: string|null,
 *                    conversacion: string, expira_en_segundos: number}>}
 *          Lanza `FalloDeRed('sin-sesion')` cuando no hay sesión.
 */
export async function consultar({ señal } = {}) {
  return pedir(RUTAS.sesion, { señal });
}

/**
 * Abre sesión con la identidad de Google · `DD-18` · `PM-B15`.
 *
 * Lo único que cruza es el `id_token` que Google acaba de firmar. **El rol no
 * se manda**: lo decide el servidor consultando su registro de docentes, y
 * mandarlo desde aquí sería exactamente el agujero que `PM-B15` cerró —hasta
 * entonces `{"rol":"docente"}` en el cuerpo bastaba para pasar la guarda—.
 *
 * Tampoco se guarda el token. Se entrega, el servidor responde con su cookie
 * de sesión y el token deja de hacer falta: conservarlo en el cliente sería
 * tener dos credenciales vivas donde basta una.
 */
export async function iniciarConGoogle(idToken, { señal } = {}) {
  const invitacion = typeof location === 'undefined'
    ? ''
    : new URLSearchParams(location.search).get('invitacion') ?? '';
  return pedir(RUTAS.sesionGoogle, {
    metodo: 'POST',
    cuerpo: { id_token: idToken, ...(invitacion ? { invitacion } : {}) },
    señal
  }).then((respuesta) => {
    if (invitacion && typeof history !== 'undefined') {
      const url = new URL(location.href);
      url.searchParams.delete('invitacion');
      history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
    }
    return respuesta;
  });
}

/** Cierra sesión. */
export async function cerrar({ señal } = {}) {
  return pedir(RUTAS.sesion, { metodo: 'DELETE', señal });
}

/**
 * Cuánto le queda a la sesión. **NO la prolonga**, pese al nombre de la ruta.
 *
 * `rutas/sesion.py::renovar` es explícito: los siete días de `EQ-020` se
 * cuentan desde que la sesión se abrió, y renovarlos al consultarlos
 * convertiría el plazo en «siete días sin cerrar la pestaña». Lo que devuelve
 * es `expira_en_segundos`, que es lo que hace falta para avisar antes de tiempo.
 *
 * Se publican los segundos que faltan y no el instante de vencimiento porque un
 * plazo relativo no depende del reloj del navegador: uno adelantado avisaría
 * tarde y uno atrasado no avisaría nunca.
 */
export async function tiempoRestante({ señal } = {}) {
  return pedir(RUTAS.renovar, { metodo: 'POST', señal });
}

/**
 * Acredita una reautenticación reciente · `EQ-022`.
 *
 * Manda un `id_token` **nuevo** de Google y nada más. El servidor comprueba
 * firma, audiencia, dominio institucional, que el `sub` sea el de esta sesión y
 * —desde el hito R7-A— que Google lo haya firmado hace un momento; sólo
 * entonces anota la acreditación con su propio reloj.
 *
 * El token no se guarda aquí, igual que en `iniciarConGoogle()`: se entrega y
 * deja de hacer falta. La prueba vive en el servidor y `POST /api/datos/supresion`
 * la consume sin que el cliente le mande ninguna fecha.
 *
 * @returns {Promise<{reautenticada: boolean, vigente_por_segundos: number,
 *                    acreditada_en: string}>}
 */
export async function reautenticar(idToken, { señal } = {}) {
  return pedir(RUTAS.reautenticar, {
    metodo: 'POST',
    cuerpo: { id_token: idToken },
    señal
  });
}

/**
 * «Nueva conversación»: otro hilo, **la misma sesión autenticada**.
 *
 * ⚠️ **Aquí decía que cerraba la sesión y abría otra, y era la mitad del hito
 * R1.** Con aquella lectura, empezar una conversación cada seis días conservaba
 * la sesión para siempre y el plazo de `EQ-020` dejaba de existir justo para
 * quien más usa el tutor. El servidor ya no lo hace: `reiniciar_sesion` genera
 * un identificador de **conversación** nuevo y conserva token, `creada_en`,
 * identidad, rol y la prueba de reautenticación si la había.
 *
 * Lo que cambia es el hilo; lo que se conserva es la autenticación y su
 * vencimiento. No es `cerrar()` seguido de volver a entrar —ese camino sí exige
 * pasar otra vez por Google—.
 */
export async function reiniciar({ señal } = {}) {
  return pedir(RUTAS.reiniciarSesion, { metodo: 'POST', señal });
}

/*
 * ⚠️ `resolverConsentimiento()` SE RETIRÓ EN C1, Y NO SE SUSTITUYE POR UN ALIAS.
 *
 * Llamaba a `POST /api/consentimiento` a través de `RUTAS.consentimiento`, una
 * constante que **nunca existió** en la tabla —`pedir(undefined)` habría pedido
 * `/apiundefined`—, y la pantalla lo esquivaba escribiendo la ruta a mano. Esa
 * ruta responde hoy **410**: escribía la decisión en un `dict` de memoria y en
 * `consentimiento_usuario`, y al declarar una edad menor de 18 ejecutaba una
 * cascada de borrado. Ninguna de las tres cosas admite `EQ-016`/`EQ-021`.
 *
 * El recorrido vigente vive en `api/consentimiento.js` y el perfil en
 * `api/onboarding.js`. Dejar aquí una función que reenviara a la ruta nueva
 * habría escondido que la semántica cambió entera: ya no se manda la edad con
 * la decisión, ya no se elige versión y ya no hay una sola llamada.
 */
