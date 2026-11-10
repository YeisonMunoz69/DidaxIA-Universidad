import { RUTAS, pedirPorPartes } from './cliente.js';
import { normalizar } from '../fases/catalogo.js';
import { sanear } from '../errores/degradacion.js';
import { paraEnviar } from '../formato/notaciones.js';

export const ESPERA_TURNO_MS = 75_000;

function soloElContrato(respuesta) {
  const nodo = String(respuesta?.nodo ?? '').trim();
  const resultado = String(respuesta?.resultado ?? '').trim();
  const razon = String(respuesta?.razon ?? '').trim();
  if (!nodo || !resultado || !razon) return null;
  return { nodo, resultado, razon };
}

export async function enviarTurno(
  { sesion, mensaje, notacion = '', retomarSesion = '', dosNiveles = null, idempotencia = '' },
  { alFase, señal } = {}
) {
  const fases = [];
  let cuerpo = null;
  let degradado = null;

  const anotarFase = (recibida) => {
    const f = normalizar(recibida);
    if (!f) return false;
    fases.push(f);
    alFase?.(f);
    return true;
  };

  const parte = (p) => {
    if (!p || typeof p !== 'object') return;
    if (typeof p.fase === 'string') anotarFase(p);
    if (Array.isArray(p.fases)) for (const f of p.fases) anotarFase(f);
    if (p.cuerpo) cuerpo = p.cuerpo;
    if (p.degradado) degradado = p.degradado;
  };

  await pedirPorPartes(RUTAS.turno, {
    cuerpo: {
      sesion,
      mensaje,
      momento: new Date().toISOString(),
      ...(paraEnviar(notacion) ? { notacion: paraEnviar(notacion) } : {}),
      ...(retomarSesion ? { retomar_sesion: retomarSesion } : {}),
      ...(idempotencia ? { idempotencia } : {}),
      ...(soloElContrato(dosNiveles) ? { dos_niveles: soloElContrato(dosNiveles) } : {})
    },
    alParte: parte,
    señal,
    espera: ESPERA_TURNO_MS
  });

  const respuesta = sanear({ fases, cuerpo, degradado });

  if (!respuesta.cuerpo && !respuesta.degradado) {
    return {
      ...respuesta,
      degradado: {
        situacion: 'degradado',
        ultima_fase: fases.length ? fases[fases.length - 1].texto : '',
        explicacion: 'la respuesta llegó incompleta'
      }
    };
  }
  return respuesta;
}
