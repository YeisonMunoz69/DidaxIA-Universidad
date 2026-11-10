import { FalloDeRed, clasificarEstado } from '../errores/degradacion.js';

export const BASE = '/api';

export const RUTAS = Object.freeze({
  turno: '/turno',
  sesion: '/sesion',
  sesionGoogle: '/sesion/google',
  reautenticar: '/sesion/reautenticar',
  renovar: '/sesion/renovar',
  reiniciarSesion: '/sesion/reiniciar',
  conceptos: '/conceptos',
  graficadora: '/graficadora/curvas',
  historial: '/historial',

  fuentesObras: '/fuentes/obras',
  fuentesFragmentos: '/fuentes/fragmentos',

  onboardingEstado: '/onboarding/estado',
  onboardingPerfil: '/onboarding/perfil',
  versiones: '/consentimiento/versiones',
  textoDeVersion: (codigo) =>
    `/consentimiento/version/${encodeURIComponent(codigo)}/texto`,

  decisionConjunta: '/consentimiento/decision-conjunta',

  revocarTitular: '/consentimiento/titular/revocar',
  revocarAsentimiento: '/consentimiento/asentimiento/revocar',
  formatoRepresentante: '/representante/formato',
  evidencia: '/representante/evidencia',

  evidencias: '/representante/evidencias',

  datosPersonales: '/datos-personales',
  exportarDatos: '/datos-personales/exportar',
  preferenciasNotificacion: '/preferencias-notificacion',
  configuracionSondeos: '/sondeos/configuracion',
  supresion: '/datos/supresion',
  retencion: '/datos/retencion'
});

export const ESPERA_MS = 30_000;

function cabeceras(extra) {
  return { 'Content-Type': 'application/json', Accept: 'application/json', ...extra };
}

function conTiempoLimite(ms, señalExterna) {
  const control = new AbortController();
  const reloj = setTimeout(() => {
    control.motivo = 'tiempo';
    control.abort();
  }, ms);
  señalExterna?.addEventListener('abort', () => control.abort(), { once: true });
  return {
    señal: control.signal,
    motivo: () => control.motivo,
    soltar: () => clearTimeout(reloj)
  };
}

function conMotivo(error, motivo) {
  if (error?.name === 'AbortError' && motivo) error.motivo = motivo;
  return error;
}

async function cuerpoDeError(respuesta) {
  try {
    const documento = await respuesta.json();
    return documento && typeof documento === 'object' ? documento : null;
  } catch {
    return null;
  }
}

export async function pedirBinario(
  ruta,
  { contenido, tipo, metodo = 'POST', señal, espera = ESPERA_MS } = {}
) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: { 'Content-Type': tipo, Accept: 'application/json' },
      credentials: 'include',
      body: contenido,
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }
  try {
    return await respuesta.json();
  } catch (e) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status, causa: e });
  }
}

export async function pedirArchivo(
  ruta,
  { tipo = 'application/pdf', metodo = 'GET', cuerpo, señal, espera = ESPERA_MS } = {}
) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cuerpo === undefined
        ? { Accept: tipo }
        : { Accept: tipo, 'Content-Type': 'application/json' },
      credentials: 'include',
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }

  const declarado = respuesta.headers?.get?.('content-type') ?? '';
  if (!declarado.toLowerCase().startsWith(tipo)) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status });
  }

  const documento = await respuesta.blob();
  if (!documento || documento.size === 0) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status });
  }
  return documento;
}

export async function pedir(ruta, { metodo = 'GET', cuerpo, señal, espera = ESPERA_MS } = {}) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cabeceras(),
      credentials: 'include',
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }
  if (respuesta.status === 204) return null;

  try {
    return await respuesta.json();
  } catch (e) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status, causa: e });
  }
}

export async function pedirPorPartes(ruta, { cuerpo, alParte, señal, espera = ESPERA_MS } = {}) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: 'POST',
      headers: cabeceras({ Accept: 'application/x-ndjson, text/event-stream, application/json' }),
      credentials: 'include',
      body: JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  }

  try {
    if (!respuesta.ok) {
      throw new FalloDeRed(clasificarEstado(respuesta.status), {
        estado: respuesta.status,
        cuerpo: await cuerpoDeError(respuesta)
      });
    }

    const tipo = respuesta.headers?.get?.('content-type') ?? '';
    const porLineas = tipo.includes('ndjson') || tipo.includes('event-stream');

    if (!porLineas || !respuesta.body?.getReader) {
      const documento = await respuesta.json();
      alParte?.(documento);
      return documento;
    }

    return await leerLineas(respuesta.body, alParte);
  } catch (e) {
    if (e instanceof FalloDeRed) throw e;
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'turno-interrumpido',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }
}

async function leerLineas(cuerpo, alParte) {
  const lector = cuerpo.getReader();
  const decodificador = new TextDecoder();
  let pendiente = '';
  let ultima = null;

  const entregar = (linea) => {
    const limpia = linea.trim().replace(/^data:\s*/, '');
    if (!limpia || limpia === '[DONE]') return;
    let objeto;
    try {
      objeto = JSON.parse(limpia);
    } catch {
      return;
    }
    ultima = objeto;
    alParte?.(objeto);
  };

  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;
    pendiente += decodificador.decode(value, { stream: true });
    const lineas = pendiente.split('\n');
    pendiente = lineas.pop() ?? '';
    for (const l of lineas) entregar(l);
  }
  if (pendiente) entregar(pendiente);
  return ultima;
}
