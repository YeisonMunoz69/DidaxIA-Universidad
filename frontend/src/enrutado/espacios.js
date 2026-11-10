/**
 * espacios.js — El espacio de trabajo, que NO es un rol · `EQ-031`
 * ================================================================
 *
 * `EQ-031` (Yeison, 2026-09-06) concede a docente e investigador un **modo
 * Tutor** con las herramientas funcionales del estudiante, y lo dice con estas
 * palabras: *«esta elección cambia el contexto de uso, no la identidad ni los
 * permisos de fondo»*. Este módulo es la mitad de cliente de esa decisión.
 *
 * ⚠️ NO ES UN SEGUNDO SISTEMA DE ROLES, Y CONVIENE LEER POR QUÉ
 * --------------------------------------------------------------
 * `rol` lo decide el servidor y sólo el servidor (`RP-17`). Aquí no se guarda,
 * no se deriva y no se corrige: **se recibe**. Lo único que vive en este módulo
 * es qué espacios tiene disponibles cada rol, cuál es el suyo por defecto y qué
 * árbol de componentes monta cada uno.
 *
 * La consecuencia práctica, y es la que hay que conservar: `espaciosDe()` NUNCA
 * concede. Un estudiante que guarde `profesional` a mano en su navegador sigue
 * recibiendo el espacio Tutor, porque el rol con el que se valida viene del
 * servidor. Una preferencia de interfaz no puede abrir una pantalla.
 *
 * POR QUÉ EL ÁRBOL SE DERIVA DE AQUÍ Y YA NO SÓLO DEL ROL
 * --------------------------------------------------------
 * `DD-04` decidió que la frontera que protege algo es **estudiante frente a
 * no-estudiante**, y eso sigue intacto: es la frontera del vector conductual.
 * Lo que cambia es quién la cruza. Hasta `EQ-031` el rol determinaba el árbol
 * de por vida; ahora un docente en espacio Tutor monta el árbol del estudiante
 * —conversación, conceptos, biblioteca— **sin dejar de ser docente**.
 *
 * Que monte ese árbol no le da el modelo del estudiante: `puedeVerVectorConductual()`
 * sigue preguntando por el ROL en `nucleo/sesion/rol.js`, y `rutas.js` sólo le
 * ofrece las rutas marcadas `tutorProfesional`. El ciclo de vida académico
 * —matrícula, consentimiento, perfil— no es suyo y no se le abre.
 *
 * EL FALLO SEGURO APUNTA AL MISMO LADO QUE SIEMPRE
 * -------------------------------------------------
 * `esEstudiante()` trata como estudiante cualquier rol que no reconozca, para
 * que una errata del servidor no abra el panel conductual. Aquí se hereda tal
 * cual: un rol desconocido recibe `['tutor']`, así que no puede elegir espacio
 * y nunca monta el árbol profesional. Al revés —lo desconocido es personal
 * autorizado— una errata abriría la cola de supervisión.
 *
 */
import { esEstudiante } from '../nucleo/sesion/rol.js';

/** Las capacidades de consulta del estudiante, usadas por cualquier rol. */
export const ESPACIO_TUTOR = 'tutor';

/** La cola, las clases y las evidencias: el panel propio de cada profesional. */
export const ESPACIO_PROFESIONAL = 'profesional';

/**
 * Los dos, y no hay un tercero.
 *
 * En este orden porque el Tutor es el que existe para todo el mundo; el
 * profesional es el que hay que merecer. Quien recorra la lista y se olvide de
 * filtrar ofrece el común, no el reservado.
 */
export const ESPACIOS = Object.freeze([ESPACIO_TUTOR, ESPACIO_PROFESIONAL]);

/**
 * Los espacios de un rol, **el predeterminado primero**.
 *
 * Que el primero sea el defecto no es un detalle de estilo: evita una segunda
 * tabla `rol → espacio inicial` que pudiera discrepar de ésta. Una sola lista
 * responde «cuáles tiene» y «con cuál empieza».
 */
export function espaciosDe(rol) {
  if (esEstudiante(rol)) return [ESPACIO_TUTOR];
  return [ESPACIO_PROFESIONAL, ESPACIO_TUTOR];
}

/** ¿Hay algo que elegir? El estudiante no necesita selector y no lo ve. */
export function puedeElegirEspacio(rol) {
  return espaciosDe(rol).length > 1;
}

/**
 * Dónde aterriza este rol mientras no elija.
 *
 * El espacio profesional para docente e investigador: entran a trabajar, y el
 * Tutor es la excursión. No hay ninguna decisión vigente que diga lo contrario
 * —se buscó en `DECISIONES.md` y en la hoja de ruta— así que se sigue el
 * encargo de Fase 7 §5.1.
 */
export function espacioPredeterminadoDe(rol) {
  return espaciosDe(rol)[0];
}

/** ¿Este rol puede estar en este espacio? Allowlist, nunca lista negativa. */
export function espacioValido(espacio, rol) {
  return espaciosDe(rol).includes(espacio);
}

/**
 * El espacio con el que se trabaja de verdad, validado contra el rol del servidor.
 *
 * **Es la puerta por la que pasa todo valor de fuera** —`localStorage`, una
 * dirección, una prueba—. Un valor que no corresponda al rol no es un error que
 * reportar: es una preferencia que dejó de aplicar —cambió la cuenta, cambió el
 * rol, alguien la editó a mano— y se resuelve cayendo al predeterminado.
 */
export function normalizarEspacio(espacio, rol) {
  return espacioValido(espacio, rol) ? espacio : espacioPredeterminadoDe(rol);
}

/**
 * El árbol de componentes que monta este rol en este espacio.
 *
 * ⚠️ **Sin `espacio`, el resultado es exactamente el de antes de `EQ-031`.**
 * Es lo que permite que las guardas, la navegación y las pruebas que aún no
 * hablan de espacios sigan diciendo lo mismo: el predeterminado de un
 * estudiante es el Tutor y el de un profesional es el suyo, así que
 * `arbolDe('docente')` sigue dando `no-estudiante`.
 */
export function arbolDe(rol, espacio) {
  return normalizarEspacio(espacio, rol) === ESPACIO_PROFESIONAL
    ? 'no-estudiante'
    : 'estudiante';
}
