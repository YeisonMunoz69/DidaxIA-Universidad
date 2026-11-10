/**
 * Las notaciones de derivada que el estudiante puede elegir. `D-21` · `PM-B32`.
 *
 * Lista CERRADA, como la de fases: lo que no está aquí no se ofrece y no se
 * envía. Ampliarla es enmendar `D-21`, no añadir una constante.
 *
 * QUÉ DECIDE ESTO Y QUÉ NO
 * -------------------------
 * Decide **qué se le puede pedir al servidor**. NO decide cómo se dibuja: eso
 * lo hace el motor simbólico, y el cliente pinta lo que llegue.
 *
 * Y ésa es la parte importante. La tentación es traducir aquí el LaTeX que
 * llega —cambiar `\dfrac{d}{dx}` por `f'` con una expresión regular— y sería
 * el mismo error que `nucleo/api/turno.js` evita al no normalizar la entrada:
 * **habría dos autoridades sobre la notación** y la que el estudiante ve
 * dejaría de ser la que el motor calculó. El cliente elige y transporta; el
 * servidor escribe.
 *
 * DE DÓNDE SALEN LAS CUATRO, Y POR QUÉ NO HAY UNA QUINTA
 * -------------------------------------------------------
 * `D-21`, ratificada el 2026-08-14. Contadas sobre las cinco obras del corpus
 * ese mismo día, por encabezado y por cuerpo:
 *
 *     f'(x)   Lagrange    1776 apariciones · 5 de 5 obras
 *     dy/dx   Leibniz      741 apariciones · 5 de 5 obras
 *     d/dx    operador     468 apariciones · 4 de 5 obras
 *     D_x[·]  Euler        194 apariciones · 2 de 5 obras
 *     y con punto  Newton    0 apariciones · 0 de 5 obras
 *
 * **Newton queda fuera por la cifra, y Euler entra por la misma** (`PM-F11`,
 * `D-21` capa del 2026-08-14). Las dos obras que la usan son Purcell y
 * Leithold, y `corpus/FUENTES.md` dice que el microcurrículo prescribe cuatro
 * —`LEI`, `PIS`, `PUR`, `SWO`—: son dos de las cuatro. Un catálogo que excluye
 * por la cifra y luego ignora la cifra no es un catálogo, es una preferencia.
 *
 * EULER VA JUNTO AL OPERADOR, Y NO AL FINAL · esto es la mitad de `PM-F11`
 * ------------------------------------------------------------------------
 * **No es una cuarta manera de pensar la derivada: es la otra grafía del mismo
 * operador.** Leithold enseña `d/dx[f(x)]` y `D_x[f(x)]` **en la misma frase**,
 * y `pasos.py` lo tiene escrito desde antes de que esto se pudiera elegir: las
 * dos aplican un operador a una expresión, mientras que `dy/dx` es la derivada
 * de una `y` que tiene que existir y `f'(x)` es una función nueva.
 *
 * Por eso el orden de este objeto **no es decorativo** —`ADMITIDAS` sale de él
 * y es el orden en que se pintan los radios—, y por eso los dos `ejemplo`
 * comparten la forma `[ f(x) ]`: quien no conozca `D_x` tiene que poder ver de
 * qué es pariente sin que nadie se lo explique.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md §3.ter
 */

/**
 * Las cuatro, con cómo se llaman y cómo se ven.
 *
 * El `ejemplo` va en texto plano y no en LaTeX **a propósito**: se lee en un
 * control de formulario, donde no hay KaTeX, y una fórmula a medio renderizar
 * en el sitio donde se elige cómo ver las fórmulas sería una broma cruel.
 *
 * El nombre de Euler es **«Operador de Euler»** y no «Euler» a secas: la
 * etiqueta corta dejaría a dos vecinos llamados «Operador» y «Euler» sin decir
 * en ninguna parte que son la misma idea, y el parentesco es justo lo que hay
 * que poder ver aquí.
 */
export const NOTACIONES = Object.freeze({
  operador: { nombre: 'Operador', ejemplo: 'd/dx [ f(x) ]' },
  euler: { nombre: 'Operador de Euler', ejemplo: 'D_x [ f(x) ]' },
  lagrange: { nombre: 'Lagrange', ejemplo: "f'(x)" },
  leibniz: { nombre: 'Leibniz', ejemplo: 'dy/dx' }
});

/** Los identificadores admitidos, en el orden en que se ofrecen. */
export const ADMITIDAS = Object.freeze(Object.keys(NOTACIONES));

/**
 * La que ve quien no ha elegido nunca.
 *
 * Es el operador porque **es lo que el sistema ya emitía** antes de que se
 * pudiera elegir: los pasos venían en `\dfrac{d}{dx}[·]`. Poner de defecto la
 * más frecuente del corpus —Lagrange— habría cambiado el aspecto de cada
 * desarrollo del sistema por una decisión que nadie tomó.
 *
 * ⚠️ Este valor tiene un gemelo en el servidor —`NOTACION_POR_DEFECTO` de
 * `pasos.py`— y **no se comprueba solo**: el cliente manda vacío cuando no hay
 * preferencia, precisamente para que decida el servidor y no haya dos defectos.
 * Éste es para pintar el control, no para enviarlo.
 */
export const POR_DEFECTO = 'operador';

/**
 * ¿Se puede pedir esta notación?
 *
 * @param {string} id
 * @returns {boolean}
 */
export function admitida(id) {
  return typeof id === 'string' && Object.hasOwn(NOTACIONES, id);
}

/**
 * Lo que se envía al servidor: el identificador, o cadena vacía.
 *
 * **Vacía y no el defecto**, que es la decisión de este módulo: si el cliente
 * mandara `operador` cuando el estudiante no ha elegido, el defecto pasaría a
 * estar en dos sitios y cambiarlo en el servidor dejaría de cambiarlo. Vacío
 * significa «decide tú», y el servidor es quien sabe qué sabe escribir.
 *
 * @param {string} id
 * @returns {string}
 */
export function paraEnviar(id) {
  return admitida(id) ? id : '';
}
