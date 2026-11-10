/**
 * Redirecciones.
 *
 * A la entrada institucional si no hay sesión, al recorrido retenido si el
 * acceso calculado no permite lo que se pidió, y al inicio del árbol propio si
 * el rol no da para la ruta. LAS GUARDAS NO SON SEGURIDAD: son cortesía, para
 * que el usuario no llegue a una pantalla que el servidor le va a negar. La
 * negativa efectiva la ejerce el servidor, siempre.
 *
 * EL ORDEN DE LAS TRES COMPROBACIONES ES LA DECISIÓN
 * ---------------------------------------------------
 * 1. ¿Existe la ruta? Si no, **no se redirige** — ver `T-13` más abajo.
 * 2. ¿Es de este árbol? Si no, al inicio del suyo. **Antes que el acceso**,
 *    porque mandar a un docente al recorrido de consentimiento del estudiante
 *    sería mandarlo a un trámite que no es suyo.
 * 2.bis. ¿Es de su ROL? · C2B. Una ruta puede declarar una allowlist dentro de
 *    su árbol —hoy sólo `/evidencias`, que `EQ-023` reserva al investigador— y
 *    una docente que la escriba a mano acaba en la suya. Va aquí y no al final
 *    porque responde a la misma pregunta que el paso 2: «esta pantalla no es
 *    tuya».
 * 3. ¿El `acceso` calculado alcanza esta ruta? Si no, a donde corresponda.
 *
 * ⚠️ **Y el inicio se pide con `inicioDe(rol)`, nunca con un mapa por árbol.**
 * `INICIO['no-estudiante']` mandaba a una investigadora a `/supervision`, que no
 * es su cola. Ahora hay una sola función y la usan guardas, navegación y
 * pruebas; ver `rutas.js`.
 *
 * ⚠️ LO QUE SE RETIRÓ EN C1, Y POR QUÉ NO ERA UN AJUSTE DE NOMBRE
 * -----------------------------------------------------------------
 * Aquí la única pregunta era `consentimiento === 'pendiente'`, sobre un campo
 * del `dict` de sesión del servidor. Ese campo dejó de ser autoridad: la
 * decisión vigente vive en `consentimiento_evento` y el acceso lo **calcula**
 * `dominio/modelo/acceso.py` a partir de perfil, versión requerida, categoría
 * de edad, asentimiento y representante. Con la pregunta antigua:
 *
 *   · un menor con el consentimiento del titular otorgado y **sin autorización
 *     del representante** pasaba la guarda y llegaba al tutor;
 *   · alguien que **revocó** pasaba igual, porque `revocado` no es `pendiente`;
 *   · alguien cuyo consentimiento era de una versión ya desplazada pasaba
 *     también, porque el campo seguía diciendo `otorgado`.
 *
 * Y la tercera cosa que decía esta cabecera —«rechazar el tratamiento no cierra
 * el tutor, `RP-19`»— quedó sustituida por `EQ-016`: hoy rechazar o revocar
 * **sí** bloquea, porque el consentimiento cubre las finalidades obligatorias
 * declaradas y no un tratamiento opcional. No es que la regla anterior se
 * aplicara mal: es que el contrato humano que la sostenía cambió.
 *
 * `T-13` · «NO EXISTE» NO ES UN PERMISO QUE NEGAR
 * --------------------------------------------------
 * Hasta el 2026-08-20 el paso 1 hacía lo mismo que el 2: `return
 * INICIO[arbol]`. La raíz reescribe la URL cuando `destino !== camino`
 * —§4—, así que pedir `/no-existe` reescribía la dirección a `/` **antes de
 * que nadie la viera**: no había ni siquiera un instante en el que se
 * pudiera copiar para reportarla. Medido en el navegador el 2026-08-20.
 *
 * «Este camino no existe» y «su rol no puede entrar» son dos hechos
 * distintos y merecen dos respuestas distintas: la primera no tiene a dónde
 * mandar a nadie —no hay una pantalla «correcta» para una URL inventada—,
 * así que ya no redirige. Devuelve `pedido` tal cual, y es la vista —no la
 * guarda— quien decide qué se pinta cuando la ruta no existe.
 *
 */
import { inicioDe } from './caminos.js';
import { puedeAbrir, rutaDe } from './rutas.js';
import { esEstudiante } from '../nucleo/sesion/rol.js';
import { alcanzable, destinoDe, SIN_CONSULTAR } from '../nucleo/sesion/acceso.js';

export { arbolDe, navegar } from './navegar.js';

/**
 * A dónde hay que ir de verdad, dado lo que se pidió y quién lo pide.
 *
 * Devuelve **siempre un camino**, nunca `null`: una guarda que a veces no
 * decide obliga a quien la llama a repetir el criterio, y repetido acaba
 * divergiendo.
 *
 * @param {string} pedido  el camino que se pidió
 * @param {{rol: string, acceso: string, autenticada: boolean}} quien
 * @returns {string} el camino al que se debe ir
 */
export function resolver(pedido, quien) {
  const ruta = rutaDe(pedido);

  // 1 · no existe. No se redirige — ver `T-13` en la cabecera.
  if (!ruta) return pedido;

  // 2 · no es suya: ni de su árbol, ni de su rol, ni de su espacio · `EQ-031`.
  //
  // Las tres preguntas viven juntas en `rutas.js::puedeAbrir()` y se resuelven
  // antes que el acceso, a propósito: mandar a un docente al recorrido de
  // consentimiento del estudiante sería mandarlo a un trámite que no es suyo.
  //
  // Antes eran dos comprobaciones escritas aquí —árbol y `rolPermitido`— y la
  // tercera, el espacio, habría sido la tercera copia de la misma decisión: la
  // navegación de `rutasDeZona()` tiene que responder exactamente lo mismo o la
  // aplicación ofrece un enlace que esta guarda rebota. Ahora hay una matriz y
  // los dos la consultan.
  //
  // Y sigue sin ser seguridad. `GET /api/representante/evidencias` responde 403
  // a la misma docente aunque llegue con las herramientas del navegador; esto
  // sólo evita que llegue a una pantalla que el servidor le va a negar.
  if (!puedeAbrir(ruta, quien?.rol, quien?.espacio)) {
    return inicioDe(quien?.rol, quien?.espacio);
  }

  // 3 · el acceso calculado. Sólo gobierna a un ESTUDIANTE: el recorrido de
  // `EQ-020` —perfil, consentimiento, representante— es suyo y nadie más tiene
  // uno que completar.
  //
  // ⚠️ **Se pregunta por el rol y no por el árbol, y desde `EQ-031` no es lo
  // mismo.** Un docente en espacio Tutor monta el árbol del estudiante; con la
  // condición anterior (`arbol === 'estudiante'`) su acceso —que vale
  // `sin_consultar`, porque `refrescarAcceso()` no pregunta el onboarding de
  // quien no lo tiene— habría hecho inalcanzable `/` y lo habría mandado al
  // consentimiento del estudiante en bucle.
  if (esEstudiante(quien?.rol)) {
    // Sin sesión, el árbol entero se reduce a la entrada institucional, que es
    // lo que `/consentimiento` pinta cuando no hay nadie identificado. No hay
    // vía anónima que llevar a ninguna otra parte.
    const acceso = quien?.autenticada === false ? SIN_CONSULTAR : (quien?.acceso ?? SIN_CONSULTAR);
    if (!alcanzable(pedido, acceso, quien?.tutoriaAcademicaSinInvestigacion)) {
      return destinoDe(acceso);
    }
  }

  // 4 · un acceso heredado conserva las guardas anteriores, pero no monta una
  // segunda pantalla. `replaceState` en la raíz evita dejar el alias en atrás.
  return ruta.redirigirA ?? pedido;
}

/** ¿Hace falta redirigir? Cómoda para no comparar dos veces en el componente. */
export function redirige(pedido, quien) {
  return resolver(pedido, quien) !== pedido;
}

/**
 * Cambia de pantalla desde cualquier componente.
 *
 * Vive aquí y no en la raíz porque si no, cada pantalla que quiera navegar
 * necesitaría que le pasaran una función desde arriba, y la que se olvide
 * acabará tocando `history` por su cuenta — con lo que la aplicación dejaría de
 * enterarse del cambio.
 *
 * `resolver()` NO se aplica aquí. Quien navega dice a dónde quiere ir; si no
 * le corresponde, la guarda de la raíz lo devolverá. Aplicarlo en los dos
 * sitios escondería el rebote y haría imposible saber qué se pidió.
 */
