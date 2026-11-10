/**
 * Los siete estados de acceso, y qué se puede alcanzar en cada uno.
 *
 * Es la mitad de cliente de `dominio/modelo/acceso.py`. El backend **calcula**
 * el estado —no existe una columna que alguien pueda poner en `habilitado`— y
 * lo publica en `GET /api/onboarding/estado` como `acceso`. Este archivo no lo
 * vuelve a derivar: lo lee, y decide con él qué pantallas ofrecer.
 *
 * POR QUÉ NO SE RECALCULA AQUÍ, AUNQUE HAYA DATOS DE SOBRA
 * ----------------------------------------------------------
 * La respuesta trae perfil, consentimiento, asentimiento, representante y las
 * versiones requeridas: con eso se podría reimplementar `calcular_acceso()`. Y
 * sería exactamente el error que la Fase 3 existe para no cometer. Dos
 * implementaciones de la misma regla divergen —basta que el equipo publique una
 * versión nueva y el cliente no compare la categoría de edad— y la que se
 * equivoca del lado peligroso es siempre la del navegador, porque es la que
 * decide qué enseñar. `acceso` es un dato del servidor y se trata como tal.
 *
 * Y ESTO SIGUE SIENDO CORTESÍA · `07` §11
 * -----------------------------------------
 * La negativa efectiva la ejerce el servidor en cada ruta. Lo que hay aquí
 * evita que alguien llegue a una pantalla que el backend le va a negar. Si
 * fuera lo único que separa el tutor de quien no lo tiene autorizado, bastaría
 * abrir las herramientas del navegador para saltárselo — y no lo es.
 *
 */

/** Los siete de la tabla aprobada. Ninguno se escribe: todos se derivan. */
export const ACCESOS = Object.freeze([
  'onboarding_pendiente',
  'esperando_representante',
  'habilitado',
  'bloqueado_por_rechazo',
  'bloqueado_por_revocacion',
  'eliminacion_solicitada',
  'mantenimiento'
]);

/**
 * El estado con el que se arranca, antes de saber nada.
 *
 * No es `mantenimiento` ni `habilitado`: es «todavía no he preguntado». Se
 * declara con nombre propio para que ninguna comprobación lo confunda con un
 * estado real del servidor — y para que el valor por defecto de cualquier
 * variable de acceso NO habilite nada.
 */
export const SIN_CONSULTAR = 'sin_consultar';

/**
 * El único estado que abre el tutor. `EQ-016`, tabla de acceso aprobada.
 *
 * Se declara como conjunto de un elemento, igual que `ACCESOS_CON_TUTOR` en el
 * dominio, para que añadir otro sea un cambio visible en una línea y no un `if`
 * repartido por la aplicación.
 */
const CON_TUTOR = Object.freeze(['habilitado']);

/** Si el tutor se puede usar. Un solo sitio donde se responde. */
export function permiteTutor(acceso, tutoriaAcademicaSinInvestigacion = false) {
  return CON_TUTOR.includes(acceso) || (
    tutoriaAcademicaSinInvestigacion === true &&
    !['eliminacion_solicitada', 'mantenimiento'].includes(acceso)
  );
}

/**
 * Las rutas del árbol del estudiante alcanzables en cada estado.
 *
 * **Allowlist explícita y no una lista de prohibiciones.** Escrita al revés
 * —«en este estado no se puede ir a X»— una ruta nueva quedaría permitida por
 * omisión en los siete estados, incluido el tutor durante un bloqueo. Así, una
 * ruta que nadie añada a esta tabla simplemente no se alcanza mientras el
 * acceso no sea `habilitado`, que es el fallo barato de los dos.
 *
 * `habilitado` no aparece: le corresponde el árbol entero y enumerarlo aquí
 * crearía una segunda lista que mantener junto a `rutas.js`.
 *
 * De dónde sale cada fila, según la tabla de «Estados y acceso aprobados»:
 *
 * - `onboarding_pendiente` — «completar perfil y consentimiento». Incluye
 *   `/unirse` porque la vinculación a clase es uno de los cuatro campos que
 *   `EQ-020` exige confirmar y el recorrido para conseguirla ya existe; sin
 *   ella el perfil nunca llega a estar completo y el estado no avanza jamás.
 * - `esperando_representante` — «descargar/cargar evidencia y consultar
 *   estado», más perfil y derechos del titular.
 * - los dos bloqueos — «derechos del titular y nueva aceptación».
 * - `eliminacion_solicitada` — «cancelar dentro del plazo y consultar estado».
 * - `mantenimiento` — «información pública y estado del servicio»: se llega a
 *   la pantalla que explica el mantenimiento y a nada más, porque nada más se
 *   puede afirmar mientras la base no responda.
 */
const ALCANZABLES = Object.freeze({
  onboarding_pendiente: ['/consentimiento', '/unirse', '/mis-datos'],
  esperando_representante: ['/consentimiento', '/mis-datos'],
  bloqueado_por_rechazo: ['/consentimiento', '/mis-datos'],
  bloqueado_por_revocacion: ['/consentimiento', '/mis-datos'],
  eliminacion_solicitada: ['/consentimiento', '/mis-datos'],
  mantenimiento: ['/consentimiento'],
  // Antes de la primera respuesta no se ofrece nada que dependa del estado: no
  // se sabe cuál es, y suponer el permisivo enseñaría el tutor por un instante
  // a quien lo tiene bloqueado.
  [SIN_CONSULTAR]: ['/consentimiento']
});

/** Las rutas alcanzables en ese estado, o `null` si lo son todas. */
export function rutasAlcanzables(acceso, tutoriaAcademicaSinInvestigacion = false) {
  if (permiteTutor(acceso, tutoriaAcademicaSinInvestigacion)) return null;
  return ALCANZABLES[acceso] ?? ALCANZABLES[SIN_CONSULTAR];
}

/** ¿Este camino se puede alcanzar con este acceso? */
export function alcanzable(camino, acceso, tutoriaAcademicaSinInvestigacion = false) {
  const permitidas = rutasAlcanzables(acceso, tutoriaAcademicaSinInvestigacion);
  return permitidas === null || permitidas.includes(camino);
}

/**
 * Dónde aterriza quien no puede seguir donde pidió.
 *
 * `/consentimiento` en todos los casos menos uno: quien tiene un trámite de
 * supresión abierto va a `/mis-datos`, que es donde está el estado del trámite
 * y el botón de cancelarlo. Mandarlo a la pantalla de autorización le pediría
 * decidir sobre un consentimiento cuando lo que hizo fue pedir que se borre
 * todo, y no le enseñaría el plazo que sí le corre.
 */
export function destinoDe(acceso) {
  return acceso === 'eliminacion_solicitada' ? '/mis-datos' : '/consentimiento';
}

/**
 * Si este estado es un bloqueo que el propio recorrido puede resolver.
 *
 * Sirve a la pantalla, no a la guarda: `onboarding_pendiente` se resuelve
 * completando datos, mientras que los dos bloqueos y la eliminación solicitada
 * son situaciones que se explican antes de ofrecer nada.
 */
export function esBloqueo(acceso) {
  return acceso === 'bloqueado_por_rechazo' || acceso === 'bloqueado_por_revocacion';
}
