import * as api from '../api/sesion.js';
import { limpiarCachesDeLectura } from '../lectura/cache.js';
import * as onboarding from '../api/onboarding.js';
import { clasificar } from '../errores/degradacion.js';
import { conversacion } from '../conversacion/conversacion.svelte.js';
import { historial } from '../historial/historial.svelte.js';
import { esEstudiante } from './rol.js';
import { SIN_CONSULTAR, permiteTutor } from './acceso.js';
import { vincularCuenta, desvincularCuenta } from '../preferencias/cuenta.js';

export function crearSesion() {
  let conversacionActual = $state('');
  let rol = $state('estudiante');
  let acceso = $state(SIN_CONSULTAR);
  let tutoriaAcademicaSinInvestigacion = $state(false);
  let degradada = $state(false);
  let cargando = $state(false);
  let expiraEnSegundos = $state(0);

  let sincronizada = $state(false);

  let autenticada = $state(false);

  function aplicar(datos) {
    const eraAutenticada = autenticada;
    conversacionActual = datos?.conversacion ?? datos?.sesion ?? '';
    rol = datos?.rol ?? 'estudiante';
    autenticada = Boolean(datos);
    if (autenticada) void vincularCuenta(datos.correo ?? datos.identificador_estable ?? 'sesion-activa');
    else if (eraAutenticada) desvincularCuenta();
    expiraEnSegundos = Number(datos?.expira_en_segundos ?? 0);

    conversacion?.verificarDueno?.(conversacionActual);

    if (!autenticada) {
      limpiarCachesDeLectura();
      acceso = SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion = false;
      conversacion?.limpiar?.();
      historial?.limpiar?.();
    } else if (!eraAutenticada && esEstudiante(rol)) {
      historial?.recargarLista?.();
    }
  }

  async function refrescarAcceso() {
    if (!autenticada || !esEstudiante(rol)) {
      acceso = SIN_CONSULTAR;
      return;
    }
    try {
      const estado = await onboarding.estado();
      acceso = estado?.acceso ?? SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion =
        estado?.tutoria_academica_sin_investigacion === true;
      degradada = false;
    } catch (e) {
      const clase = clasificar(e);
      if (clase === 'sin-sesion') {
        aplicar(null);
      } else if (clase === 'mantenimiento') {
        acceso = 'mantenimiento';
      } else {
      acceso = SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion = false;
        degradada = true;
      }
    }
  }

  return {
    get conversacion() { return conversacionActual; },
    get rol() { return rol; },
    get acceso() { return acceso; },
    get tutoriaAcademicaSinInvestigacion() { return tutoriaAcademicaSinInvestigacion; },
    get degradada() { return degradada; },
    get cargando() { return cargando; },
    get sincronizada() { return sincronizada; },
    get abierta() { return autenticada; },
    get autenticada() { return autenticada; },
    get expiraEnSegundos() { return expiraEnSegundos; },
    get puedeUsarTutor() {
      return permiteTutor(acceso, tutoriaAcademicaSinInvestigacion);
    },

    async sincronizar() {
      cargando = true;
      try {
        aplicar(await api.consultar());
        degradada = false;
        await refrescarAcceso();
      } catch (e) {
        const clase = clasificar(e);
        degradada = clase !== 'sin-sesion';
        if (!degradada) aplicar(null);
      } finally {
        cargando = false;
        sincronizada = true;
      }
    },

    async refrescarAcceso() {
      await refrescarAcceso();
    },

    aplicarAcceso(valor, tutoriaAcademica = false) {
      if (typeof valor === 'string' && valor) acceso = valor;
      tutoriaAcademicaSinInvestigacion = tutoriaAcademica === true;
    },
    async entrarConGoogle(idToken) {
      aplicar(await api.iniciarConGoogle(idToken));
      degradada = false;
      await refrescarAcceso();
    },

    async reiniciarConversacion() {
      aplicar(await api.reiniciar());
      conversacion.limpiar();
      degradada = false;
    },

    async consultarVencimiento() {
      try {
        const datos = await api.tiempoRestante();
        expiraEnSegundos = Number(datos?.expira_en_segundos ?? 0);
      } catch (e) {
        if (clasificar(e) === 'sin-sesion') aplicar(null);
      }
    },

    async cerrar() {
      try {
        await api.cerrar();
      } finally {
        aplicar(null);
        conversacion?.limpiar?.();
        historial?.limpiar?.();
        sincronizada = true;
      }
    },

    marcarDegradada(v = true) { degradada = v; }
  };
}

export const sesion = crearSesion();
