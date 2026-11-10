/**
 * Lectura del rol para decidir qué se enseña.
 *
 * NO es control de acceso. El control lo ejerce el servidor. Esto solo evita
 * pintar enlaces que llevarían a un rechazo.
 *
 * LA FRONTERA QUE IMPORTA ES ESTUDIANTE FRENTE A NO-ESTUDIANTE
 * -------------------------------------------------------------
 * `DD-04` decidió que docente e investigador comparten aplicación y que lo que
 * los separa del estudiante es de otra naturaleza que lo que los separa entre
 * sí. Por eso `esEstudiante()` existe como pregunta propia y no como
 * `rol === 'docente'` negado: el día que aparezca un cuarto rol, lo que no
 * puede fallar es de qué lado del vector conductual cae.
 *
 * `esEstudiante()` es CIERTO POR DEFECTO ante un rol desconocido, y es
 * deliberado: un rol que este archivo no reconoce recibe la vista que NO
 * expone el modelo del estudiante. Al revés —tratar lo desconocido como
 * personal autorizado— un error de escritura en el servidor abriría el panel
 * conductual. `RP-18` no admite ese fallo en esa dirección.
 *
 */

/** Los roles que el servidor puede declarar. `DD-04`. */
export const ROLES = Object.freeze(['estudiante', 'docente', 'investigador']);

/** Los que NO son estudiante. Es la única frontera que protege algo. */
const NO_ESTUDIANTE = Object.freeze(['docente', 'investigador']);

/**
 * ¿Esta persona ve el árbol del estudiante?
 *
 * Cualquier rol que no esté declarado explícitamente como no-estudiante lo es.
 * Ver la cabecera: el fallo seguro es hacia el lado que no expone nada.
 */
export function esEstudiante(rol) {
  return !NO_ESTUDIANTE.includes(rol);
}

/** ¿Puede ver la cola de supervisión y la ficha de estudiante? */
export function esDocente(rol) {
  return rol === 'docente';
}

/** ¿Puede ver lo agregado con fines de investigación? */
export function esInvestigador(rol) {
  return rol === 'investigador';
}

/**
 * ¿Puede este rol ver el vector conductual?
 *
 * Existe como función propia, y no como `!esEstudiante(rol)`, porque es la
 * pregunta que el proyecto no puede permitirse responder mal. Escrita así, se
 * encuentra buscando «vector» y se lee de una sola vez.
 */
export function puedeVerVectorConductual(rol) {
  return NO_ESTUDIANTE.includes(rol);
}
