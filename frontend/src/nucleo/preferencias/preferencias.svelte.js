
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

const ESCALAS = ['normal', 'comoda', 'grande'];

function leerGuardada() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE);
    return v === null || v === undefined ? true : v === 'si';
  } catch {
    return true;
  }
}

function leerNotacion() {
  try {
    const v = globalThis.localStorage?.getItem(CLAVE_NOTACION);
    return admitida(v) ? v : '';
  } catch {
    return '';
  }
}


function leerVisible(clave) {
  try {
    const v = globalThis.localStorage?.getItem(clave);
    return v === null || v === undefined ? !enPantallaAmplia() : v === 'si';
  } catch {
    return !enPantallaAmplia();
  }
}

function enPantallaAmplia() {
  try {
    return globalThis.matchMedia
      ?.('(min-width: 48.0625rem)').matches ?? true;
  } catch {
    return true;
  }
}

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

function leerFondoConversacion() {
  try {
    const valor = globalThis.localStorage?.getItem(CLAVE_FONDO_CONVERSACION);
    return valor == null ? LIENZO_INICIAL.fondoConversacion : valor === 'si';
  } catch {
    return LIENZO_INICIAL.fondoConversacion;
  }
}

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

  function recordar(clave, valor) {
    try {
      globalThis.localStorage?.setItem(clave, valor ? 'si' : 'no');
    } catch {  }
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

    get tema() { return tema; },

    elegirTema(valor) {
      if (!TEMAS.includes(valor)) return;
      tema = valor;
      guardarTema(valor);
    },

    elegirEscala(valor) {
      if (!ESCALAS.includes(valor)) return;
      escalaTexto = valor;
      try {
        globalThis.localStorage?.setItem(CLAVE_ESCALA, valor);
      } catch {  }
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
      } catch {  }
    },

    elegirOpacidadPregunta(valor) {
      const numero = Number(valor);
      if (!Number.isFinite(numero)) return;
      opacidadPregunta = Math.min(100, Math.max(0, Math.round(numero)));
      try {
        globalThis.localStorage?.setItem(CLAVE_OPACIDAD_PREGUNTA, String(opacidadPregunta));
      } catch {  }
    },

    elegirOpacidadRespuesta(valor) {
      const numero = Number(valor);
      if (!Number.isFinite(numero)) return;
      opacidadRespuesta = Math.min(100, Math.max(0, Math.round(numero)));
      try {
        globalThis.localStorage?.setItem(CLAVE_OPACIDAD_RESPUESTA, String(opacidadRespuesta));
      } catch {  }
    },

    alternarGrafica(valor = !graficaVisible) {
      graficaVisible = Boolean(valor);
      try {
        globalThis.localStorage?.setItem(CLAVE, graficaVisible ? 'si' : 'no');
      } catch {  }
    },

    get notacion() { return notacion; },

    elegirNotacion(valor) {
      if (valor !== '' && !admitida(valor)) return;
      notacion = valor;
      try {
        globalThis.localStorage?.setItem(CLAVE_NOTACION, valor);
      } catch {  }
    },

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

export const preferencias = crearPreferencias();
