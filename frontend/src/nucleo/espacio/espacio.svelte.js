/**
 * espacio.svelte.js — El espacio de trabajo activo · `EQ-031`
 * ============================================================
 *
 * La **única** fuente de verdad de en qué espacio se está trabajando. No hay
 * una segunda copia en ningún componente: quien la necesite lee `espacio.activo`.
 *
 * POR QUÉ NO VIVE EN `sesion.svelte.js`, Y NO ES ORGANIZACIÓN
 * ------------------------------------------------------------
 * `sesion` conserva lo que dice **el servidor** —quién es, qué rol, qué acceso—.
 * El espacio no lo dice el servidor: lo elige la persona, y `EQ-031` lo llama
 * con todas las letras *«una preferencia de interfaz»*. Guardarlo junto al rol
 * invitaría, tarde o temprano, a que algo derivara un permiso del espacio
 * — que es exactamente lo que `EQ-031` prohíbe.
 *
 * POR QUÉ NO VIVE EN `preferencias.svelte.js` TAMPOCO
 * ----------------------------------------------------
 * Aquel módulo avisa: *«si algún día aparece aquí una segunda clave que no sea
 * una preferencia de pantalla, es que se cruzó una línea»*. El espacio **sí** es
 * una preferencia de pantalla, pero se valida contra el rol autenticado, y
 * `preferencias` no tiene por qué saber que existen roles. Se queda aparte para
 * que siga sin saberlo.
 *
 * EL ROL NO SE GUARDA EN EL NAVEGADOR, Y LA VALIDACIÓN NO LO NECESITA
 * --------------------------------------------------------------------
 * El encargo de Fase 7 lo prohíbe expresamente, y no hace falta: `activo` se
 * **deriva** en cada lectura contra `sesion.rol`, que viene del servidor. Un
 * `profesional` guardado por el docente que usó antes este navegador no coloca
 * a un estudiante en un panel ajeno — `normalizarEspacio()` lo devuelve a
 * `tutor` sin que nadie tenga que acordarse de limpiar la clave al cambiar de
 * cuenta. La preferencia caduca sola porque nunca fue una autorización.
 *
 * Y POR ESO TAMPOCO HAY DESTELLO AL SINCRONIZAR
 * -----------------------------------------------
 * Antes de que `GET /api/sesion` conteste, `sesion.rol` vale `estudiante`, así
 * que `activo` vale `tutor` aunque haya `profesional` guardado. Cuando llega el
 * rol real, `activo` pasa a `profesional` sin que este módulo haga nada: es
 * derivado, no copiado. `Aplicacion.svelte` no navega hasta
 * `sesion.sincronizada`, así que la dirección pedida tampoco se pierde.
 *
 * QUÉ NO SE GUARDA EN `localStorage`
 * -----------------------------------
 * El último destino profesional. Es estado de navegación —puede nombrar el
 * identificador de una clase— y `EQ-007` reserva el navegador a preferencias no
 * sensibles. Vive en memoria: sobrevive a cambiar de espacio y volver, que es
 * lo que `EQ-031` pide, y no a cerrar la pestaña, que nadie pidió.
 *
 */
import {
  ESPACIO_PROFESIONAL,
  ESPACIO_TUTOR,
  espacioValido,
  normalizarEspacio,
  puedeElegirEspacio
} from '../../enrutado/espacios.js';
import { inicioDe } from '../../enrutado/caminos.js';
import { sesion } from '../sesion/sesion.svelte.js';

const CLAVE = 'agente-calculo.espacio';

/**
 * Lo guardado, **sin validar contra ningún rol**.
 *
 * Devuelve la cadena cruda a propósito: validar aquí exigiría conocer el rol, y
 * al arrancar todavía no se sabe. La validación es de `activo`, que se recalcula
 * cuando el rol llega.
 */
function leerGuardado() {
  try {
    return globalThis.localStorage?.getItem(CLAVE) ?? '';
  } catch {
    // Navegación privada, almacenamiento bloqueado por la institución, o
    // simplemente no hay `localStorage` en el entorno de pruebas. Ninguna de
    // las tres impide trabajar: se cae al predeterminado del rol.
    return '';
  }
}

export function crearEspacio() {
  /** Lo que la persona eligió alguna vez. Puede no aplicar al rol de ahora. */
  let elegido = $state(leerGuardado());

  /** El último destino profesional válido, para volver donde se estaba. */
  let ultimoProfesional = $state('');

  return {
    /**
     * El espacio con el que se trabaja, ya validado contra el rol del servidor.
     *
     * Derivado y no copiado: es lo que hace que cambiar de cuenta, revocar un
     * rol o sincronizar tarde no dejen a nadie en un espacio que no es suyo.
     */
    get activo() {
      return normalizarEspacio(elegido, sesion.rol);
    },

    get esTutor() {
      return this.activo === ESPACIO_TUTOR;
    },

    get esProfesional() {
      return this.activo === ESPACIO_PROFESIONAL;
    },

    /** ¿Se le ofrece el selector? Un estudiante no tiene nada que elegir. */
    get puedeElegir() {
      return puedeElegirEspacio(sesion.rol);
    },

    /**
     * A dónde lleva cambiar de espacio.
     *
     * Al Tutor, siempre a la conversación. Al profesional, **al último destino
     * válido** —la clase que estaba mirando, la cola que estaba resolviendo— y
     * sólo si no lo hay, a su entrada canónica. `EQ-031` pide que volver no
     * pierda el trabajo, y devolver a alguien a la portada de su panel cada vez
     * que consulta algo en el Tutor lo perdería.
     */
    destinoDe(espacio) {
      const valido = normalizarEspacio(espacio, sesion.rol);
      if (valido === ESPACIO_PROFESIONAL && ultimoProfesional) return ultimoProfesional;
      return inicioDe(sesion.rol, valido);
    },

    /**
     * Recuerda dónde estaba en su panel, para volver ahí.
     *
     * Lo llama `Aplicacion.svelte` con el destino **ya resuelto por las
     * guardas**, así que nunca se guarda una dirección que la política rechace.
     * Se guarda con su consulta —`/estudiante?clase=…&id=…`— porque la ficha de
     * un estudiante sin sus parámetros no es la misma pantalla.
     */
    recordarProfesional(camino) {
      if (typeof camino === 'string' && camino) ultimoProfesional = camino;
    },

    get ultimoDestinoProfesional() {
      return ultimoProfesional;
    },

    /**
     * Cambia de espacio. **No cambia el rol, no toca la sesión y no reautentica.**
     *
     * Un valor que no corresponda al rol se ignora en silencio: no es un error
     * que reportar a nadie, es una preferencia que no aplica. Y no se escribe en
     * `localStorage` si no es válida, para no dejar guardada una elección que
     * esta cuenta nunca podrá usar.
     */
    elegir(espacio) {
      if (!espacioValido(espacio, sesion.rol)) return;
      elegido = espacio;
      try {
        globalThis.localStorage?.setItem(CLAVE, espacio);
      } catch {
        // Que no se pueda recordar no impide cambiar de espacio ahora.
      }
    }
  };
}

/**
 * La instancia que usa la aplicación. UNA sola, como `sesion` y `preferencias`.
 *
 * Un segundo espacio activo sería un segundo sistema de navegación, que es lo
 * que el encargo de Fase 7 §11 prohíbe con ese nombre.
 */
export const espacio = crearEspacio();
