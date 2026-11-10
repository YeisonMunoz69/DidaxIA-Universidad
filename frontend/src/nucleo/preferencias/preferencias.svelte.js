/**
 * DD-14 · Lo que elige el estudiante.
 *
 * Guarda dos cosas: si quiere ver la representación gráfica, y en qué notación
 * quiere leer las derivadas que el sistema le escribe (`D-21`, `PM-B32`).
 *
 * ⚠️ **Y las dos no se comportan igual, que es lo que hay que saber antes de
 * añadir una tercera.** La gráfica **no viaja al servidor**: no es dato
 * personal ni de dominio, así que el servidor sigue emitiendo el bloque
 * siempre y el cliente decide si lo pinta. La notación **sí viaja**, porque
 * quien escribe la fórmula es el motor simbólico y traducirla aquí crearía una
 * segunda autoridad sobre la notación — el mismo motivo por el que el cliente
 * no normaliza la entrada. Ver `nucleo/formato/notaciones.js`.
 *
 * Que una preferencia viaje **no la convierte en dato personal**: es una
 * preferencia de presentación que el servidor usa para escribir la respuesta
 * de ese turno y no guarda en ningún sitio.
 *
 * EL VALOR POR DEFECTO ES VISIBLE. Quien no toque nada ve la gráfica; ocultarla
 * es un acto deliberado. Al revés se perdería una ayuda que la mayoría aprovecha.
 *
 * Esta es la única carpeta donde el estudiante decide algo sobre el sistema. En
 * todo lo demás el sistema decide sobre él sin decírselo. Vive aparte de sesion/
 * por eso, no por organización.
 *
 * POR QUÉ `localStorage` AQUÍ Y EN NINGÚN OTRO SITIO
 * ---------------------------------------------------
 * Porque esto es exactamente lo que el almacenamiento del navegador es: una
 * preferencia de presentación, sin valor para nadie más, que debe sobrevivir a
 * recargar la página. La sesión no se guarda ahí —va en cookie del servidor— y
 * el modelo del estudiante tampoco, porque no llega. Si algún día aparece aquí
 * una segunda clave que no sea una preferencia de pantalla, es que se cruzó una
 * línea.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 * Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md
 */

import { LIENZO_INICIAL } from './lienzo.js';
import { admitida } from '../formato/notaciones.js';
import { guardarTema, leerTema, TEMAS } from './tema.js';
import { COLOR_INICIAL, normalizarColores } from './colores.js';
import { leerAparienciaLocal } from './aparienciaLocal.js';

const CLAVE = 'agente-calculo.grafica-visible';
const CLAVE_NOTACION = 'agente-calculo.notacion';
const CLAVE_CARRIL = 'agente-calculo.carril-visible';
const CLAVE_PANEL = 'agente-calculo.panel-visible';
const CLAVE_ESCALA = 'agente-calculo.escala-texto';
const CLAVE_ANIMACIONES = 'agente-calculo.animaciones';
const CLAVE_FONDO_CONVERSACION = 'agente-calculo.fondo-conversacion';
const CLAVE_INTENSIDAD_FONDO = 'agente-calculo.intensidad-fondo-conversacion';
const CLAVE_OPACIDAD_PREGUNTA = 'agente-calculo.opacidad-pregunta';
const CLAVE_OPACIDAD_RESPUESTA = 'agente-calculo.opacidad-respuesta';
const INTENSIDAD_FONDO_PREDETERMINADA = LIENZO_INICIAL.intensidadFondoConversacion;
const OPACIDAD_PREGUNTA_PREDETERMINADA = LIENZO_INICIAL.opacidadPregunta;
const OPACIDAD_RESPUESTA_PREDETERMINADA = LIENZO_INICIAL.opacidadRespuesta;

/** Los tres valores del tema. `sistema` sigue lo que diga el navegador. */
const ESCALAS = ['normal', 'comoda', 'grande'];

/** Lee la preferencia guardada. Ante cualquier duda, VISIBLE. */
function leerGuardada() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE);
    return v === null || v === undefined ? true : v === 'si';
  } catch {
    // Navegación privada, almacenamiento bloqueado por la institución, o
    // simplemente no hay `localStorage` en el entorno de pruebas. Ninguna de
    // las tres es motivo para esconderle la gráfica a nadie.
    return true;
  }
}

/**
 * La notación guardada, o **cadena vacía si no hay ninguna**.
 *
 * Vacía y no el defecto: es la diferencia entre «no ha elegido» y «eligió el
 * operador», y solo la primera deja que el servidor decida. Una guardada que
 * ya no esté en el catálogo —porque `D-21` se enmendó— se trata como si no
 * hubiera: se descarta en silencio y el estudiante vuelve a elegir.
 */
function leerNotacion() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE_NOTACION);
    return admitida(v) ? v : '';
  } catch {
    return '';
  }
}

/**
 * El tema guardado, o `sistema`.
 *
 * ⚠️ ES LA TERCERA CLAVE, Y LA CABECERA AVISA DE ESO. La regla que fija es que
 * aquí solo cabe una preferencia de PANTALLA, sin valor para nadie más. El tema
 * lo es: no viaja al servidor, no dice nada del estudiante, y lo único que
 * decide es de qué color se pinta la hoja.
 *
 * POR DEFECTO `sistema` Y NO `claro`. Quien configuró su equipo en oscuro suele
 * haberlo hecho por una razón —fotofobia, migraña, trabajar de noche— y abrirle
 * una pantalla blanca es desoír algo que ya dijo. Seguir al navegador es
 * respetarlo sin preguntar.
 */

/**
 * ¿Está desplegada una de las dos columnas del marco?
 *
 * Son preferencias de PANTALLA, con todas las letras: no viajan al servidor,
 * no dicen nada del estudiante, y lo único que deciden es cuánto sitio ocupa
 * la conversación. Es lo que el mockup llama «modo zen» —plegar las dos deja
 * el hilo solo— y lo que un estudiante que trabaja en un portátil de 13" va a
 * querer la primera vez que le estorbe una columna.
 *
 * En pantallas de PC y tableta empiezan plegadas. Una elección guardada manda
 * sobre el valor inicial: abrirlas deliberadamente sobrevive a la recarga.
 */
function leerVisible(clave) {
  try {
    const v = globalThis.localStorage?.getItem(clave);
    return v === null || v === undefined ? !enPantallaAmplia() : v === 'si';
  } catch {
    return !enPantallaAmplia();
  }
}

/**
 * En PC y tableta ambas columnas empiezan plegadas. En móvil la apertura
 * transitoria continúa gobernada por sus hojas y no por esta preferencia.
 *
 * Se mide UNA VEZ al arrancar, no en vivo: si el estudiante ya tomó una
 * decisión —guardada en `localStorage`— esa decisión manda en cualquier
 * ancho, porque «por defecto» describe lo que pasa ANTES del acto
 * deliberado, no una regla que reaparezca cada vez que se cambia el ancho
 * de la ventana. `48.0625rem` y no `48rem`: por debajo de `48rem` es
 * móvil —`--corte-tableta`—, y el límite tiene que ser exclusivo para no
 * solaparse con esa banda.
 */
function enPantallaAmplia() {
  try {
    return globalThis.matchMedia
      ?.('(min-width: 48.0625rem)').matches ?? true;
  } catch {
    return true;
  }
}

/** Las dos columnas comparten el valor inicial y conservan elecciones propias. */
function leerPanelVisible() {
  return leerVisible(CLAVE_PANEL);
}

function leerEscala() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE_ESCALA);
    return ESCALAS.includes(v) ? v : 'normal';
  } catch {
    return 'normal';
  }
}

function leerAnimaciones() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE_ANIMACIONES);
    return v === null || v === undefined ? true : v === 'si';
  } catch {
    return true;
  }
}

/** El ambiente del estado vacío siempre se ve; esta preferencia sólo decide
    si continúa detrás de una conversación ya iniciada. Por defecto, sí. */
function leerFondoConversacion() {
  try {
    const valor = globalThis.localStorage?.getItem(CLAVE_FONDO_CONVERSACION);
    return valor == null ? LIENZO_INICIAL.fondoConversacion : valor === 'si';
  } catch {
    return LIENZO_INICIAL.fondoConversacion;
  }
}

/** Porcentaje del ambiente que permanece detrás de una charla iniciada.

    Cero es una elección válida: mantiene habilitada la preferencia, pero deja
    el fondo completamente transparente. Una conversación nueva no consulta
    este valor; su portada matemática siempre se presenta al 100 %. */
function leerIntensidadFondo() {
  try {
    const cruda = globalThis.localStorage?.getItem(CLAVE_INTENSIDAD_FONDO);
    if (cruda === null || cruda === undefined || cruda.trim() === '') {
      return INTENSIDAD_FONDO_PREDETERMINADA;
    }
    const guardada = Number(cruda);
    return Number.isFinite(guardada) && guardada >= 0 && guardada <= 100
      ? guardada
      : INTENSIDAD_FONDO_PREDETERMINADA;
  } catch {
    return INTENSIDAD_FONDO_PREDETERMINADA;
  }
}

function leerPorcentaje(clave, predeterminado) {
  try {
    const crudo = globalThis.localStorage?.getItem(clave);
    if (crudo === null || crudo === undefined || crudo.trim() === '') return predeterminado;
    const valor = Number(crudo);
    return Number.isFinite(valor) && valor >= 0 && valor <= 100 ? valor : predeterminado;
  } catch {
    return predeterminado;
  }
}

export function crearPreferencias() {
  const aparienciaLocal=leerAparienciaLocal();
  let colores = $state(normalizarColores(aparienciaLocal ?? COLOR_INICIAL));
  let graficaVisible = $state(leerGuardada());
  let notacion = $state(leerNotacion());
  let tema = $state(aparienciaLocal?.tema ?? leerTema());
  let carrilVisible = $state(leerVisible(CLAVE_CARRIL));
  let panelVisible = $state(leerPanelVisible());
  let escalaTexto = $state(leerEscala());
  let animaciones = $state(leerAnimaciones());
  let fondoDuranteConversacion = $state(leerFondoConversacion());
  let intensidadFondoConversacion = $state(leerIntensidadFondo());
  let opacidadPregunta = $state(leerPorcentaje(
    CLAVE_OPACIDAD_PREGUNTA,
    OPACIDAD_PREGUNTA_PREDETERMINADA
  ));
  let opacidadRespuesta = $state(leerPorcentaje(
    CLAVE_OPACIDAD_RESPUESTA,
    OPACIDAD_RESPUESTA_PREDETERMINADA
  ));

  /** Guarda sin dejar que un almacenamiento bloqueado tumbe la preferencia. */
  function recordar(clave, valor) {
    try {
      globalThis.localStorage?.setItem(clave, valor ? 'si' : 'no');
    } catch { /* no poder recordarla no impide respetarla en esta sesión */ }
  }

  return {
    get colores() { return colores; },
    elegirColores(valor) { colores = normalizarColores(valor); },
    get graficaVisible() { return graficaVisible; },

    get carrilVisible() { return carrilVisible; },
    get panelVisible() { return panelVisible; },

    get escalaTexto() { return escalaTexto; },
    get animaciones() { return animaciones; },
    get fondoDuranteConversacion() { return fondoDuranteConversacion; },
    get intensidadFondoConversacion() { return intensidadFondoConversacion; },
    get opacidadPregunta() { return opacidadPregunta; },
    get opacidadRespuesta() { return opacidadRespuesta; },

    alternarCarril(valor = !carrilVisible) {
      carrilVisible = Boolean(valor);
      recordar(CLAVE_CARRIL, carrilVisible);
    },

    alternarPanel(valor = !panelVisible) {
      panelVisible = Boolean(valor);
      recordar(CLAVE_PANEL, panelVisible);
    },

    /** `sistema` · `claro` · `oscuro`. */
    get tema() { return tema; },

    /** Uno fuera de los tres no cambia nada, igual que la notación. */
    elegirTema(valor) {
      if (!TEMAS.includes(valor)) return;
      tema = valor;
      guardarTema(valor);
    },

    /** `normal` · `comoda` · `grande`. */
    elegirEscala(valor) {
      if (!ESCALAS.includes(valor)) return;
      escalaTexto = valor;
      try {
        globalThis.localStorage?.setItem(CLAVE_ESCALA, valor);
      } catch { /* no recordarlo no impide respetarlo hoy */ }
    },

    alternarAnimaciones(valor = !animaciones) {
      animaciones = Boolean(valor);
      recordar(CLAVE_ANIMACIONES, animaciones);
    },

    alternarFondoConversacion(valor = !fondoDuranteConversacion) {
      fondoDuranteConversacion = Boolean(valor);
      recordar(CLAVE_FONDO_CONVERSACION, fondoDuranteConversacion);
    },

    elegirIntensidadFondoConversacion(valor) {
      const numero = Number(valor);
      if (!Number.isFinite(numero)) return;
      intensidadFondoConversacion = Math.min(100, Math.max(0, Math.round(numero)));
      try {
        globalThis.localStorage?.setItem(
          CLAVE_INTENSIDAD_FONDO,
          String(intensidadFondoConversacion)
        );
      } catch { /* la preferencia sigue aplicándose durante esta sesión */ }
    },

    elegirOpacidadPregunta(valor) {
      const numero = Number(valor);
      if (!Number.isFinite(numero)) return;
      opacidadPregunta = Math.min(100, Math.max(0, Math.round(numero)));
      try {
        globalThis.localStorage?.setItem(CLAVE_OPACIDAD_PREGUNTA, String(opacidadPregunta));
      } catch { /* la elección sigue activa durante esta sesión */ }
    },

    elegirOpacidadRespuesta(valor) {
      const numero = Number(valor);
      if (!Number.isFinite(numero)) return;
      opacidadRespuesta = Math.min(100, Math.max(0, Math.round(numero)));
      try {
        globalThis.localStorage?.setItem(CLAVE_OPACIDAD_RESPUESTA, String(opacidadRespuesta));
      } catch { /* la elección sigue activa durante esta sesión */ }
    },

    /** Cambia la preferencia y la conserva. Si no se puede conservar, da igual. */
    alternarGrafica(valor = !graficaVisible) {
      graficaVisible = Boolean(valor);
      try {
        globalThis.localStorage?.setItem(CLAVE, graficaVisible ? 'si' : 'no');
      } catch { /* no poder recordarla no impide respetarla en esta sesión */ }
    },

    /** La elegida, o vacío si no ha elegido. Lo que se manda al servidor. */
    get notacion() { return notacion; },

    /**
     * Elige la notación · `PM-B32`.
     *
     * Una que no esté en el catálogo **no se guarda y no cambia nada**: es la
     * misma barrera que `fases/catalogo.js` pone a lo que llega del servidor,
     * aplicada aquí a lo que sale.
     *
     * `''` SÍ pasa, y es a propósito: es «sin elegir todavía» —el mismo
     * valor con el que arranca esta preferencia, ver `leerNotacion()`—, no
     * una notación inválida. `restablecer()` la usa para volver a ese
     * estado; sin este caso aparte, `admitida('')` la rechazaba igual que
     * a un id inventado y restablecer no volvía a soltar la elegida.
     */
    elegirNotacion(valor) {
      if (valor !== '' && !admitida(valor)) return;
      notacion = valor;
      try {
        globalThis.localStorage?.setItem(CLAVE_NOTACION, valor);
      } catch { /* igual que arriba: no recordarla no impide respetarla hoy */ }
    },

    /** Restablece todas las preferencias a sus valores predeterminados. */
    restablecer() {
      this.elegirColores(COLOR_INICIAL);
      this.elegirTema('sistema');
      this.elegirNotacion('');
      this.alternarGrafica(true);
      this.alternarCarril(true);
      this.alternarPanel(true);
      this.elegirEscala('normal');
      this.alternarAnimaciones(true);
      this.alternarFondoConversacion(LIENZO_INICIAL.fondoConversacion);
      this.elegirIntensidadFondoConversacion(INTENSIDAD_FONDO_PREDETERMINADA);
      this.elegirOpacidadPregunta(OPACIDAD_PREGUNTA_PREDETERMINADA);
      this.elegirOpacidadRespuesta(OPACIDAD_RESPUESTA_PREDETERMINADA);
    }
  };
}

/** La instancia que usa la aplicación. Una sola, como el estado de sesión. */
export const preferencias = crearPreferencias();
