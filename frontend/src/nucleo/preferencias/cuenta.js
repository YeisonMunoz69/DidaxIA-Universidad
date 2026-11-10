import { LIENZO_INICIAL } from './lienzo.js';
import { pedir } from '../api/cliente.js';
import { preferencias } from './preferencias.svelte.js';
import { COLOR_INICIAL, normalizarColores } from './colores.js';
import { leerAparienciaLocal, recordarAparienciaLocal } from './aparienciaLocal.js';

let titular='', generacion=0, revision=0, confirmadas={}, cola=Promise.resolve();
let cargada=false;

export function valoresInterfaz() {
  return {...preferencias.colores,tema:preferencias.tema,escalaTexto:preferencias.escalaTexto,animaciones:preferencias.animaciones,
    fondoConversacion: preferencias.fondoDuranteConversacion, intensidadFondoConversacion: preferencias.intensidadFondoConversacion,
    opacidadPregunta: preferencias.opacidadPregunta, opacidadRespuesta: preferencias.opacidadRespuesta};
}
function aplicar(datos) {
  preferencias.elegirColores(normalizarColores(datos));
  preferencias.elegirTema(datos.tema ?? 'sistema');
  preferencias.elegirEscala(datos.escalaTexto ?? 'normal');
  preferencias.alternarAnimaciones(datos.animaciones ?? true);
  preferencias.alternarFondoConversacion(datos.fondoConversacion ?? LIENZO_INICIAL.fondoConversacion);
  preferencias.elegirIntensidadFondoConversacion(datos.intensidadFondoConversacion ?? LIENZO_INICIAL.intensidadFondoConversacion);
  preferencias.elegirOpacidadPregunta(datos.opacidadPregunta ?? LIENZO_INICIAL.opacidadPregunta);
  preferencias.elegirOpacidadRespuesta(datos.opacidadRespuesta ?? LIENZO_INICIAL.opacidadRespuesta);
}
function limpiarCuenta() {
  titular=''; generacion++; cargada=false; revision=0; confirmadas={};
}
export function desvincularCuenta() {
  limpiarCuenta();
  aplicar({...COLOR_INICIAL,tema:'sistema',...leerAparienciaLocal(),escalaTexto:'normal',animaciones:true});
}
export async function vincularCuenta(id) {
  if (!id || titular===id) return;
  limpiarCuenta(); titular=id;
  const g=generacion;
  const iniciales=valoresInterfaz();
  try {
    const resultado=await pedir('/preferencias-interfaz');
    if (g!==generacion) return;
    const locales=valoresInterfaz();
    const remotas={...COLOR_INICIAL,tema:'sistema',escalaTexto:'normal',animaciones:true,
      ...LIENZO_INICIAL,
      ...resultado.preferencias,...normalizarColores(resultado.preferencias)};
    const cambios=Object.fromEntries(Object.entries(locales).filter(([k,v])=>v!==iniciales[k]));
    if (Object.keys(cambios).some(k=>k in COLOR_INICIAL)) Object.assign(cambios,preferencias.colores);
    aplicar({...remotas,...cambios});
    revision=resultado.revision ?? 0; confirmadas={...remotas}; cargada=true;
    for (const clave of Object.keys(LIENZO_INICIAL)) {
      if (!Object.prototype.hasOwnProperty.call(resultado.preferencias ?? {}, clave)) delete confirmadas[clave];
    }
    if(resultado.preferencias) recordarAparienciaLocal(remotas);
  } catch {  }
}
export function guardarInterfaz(campos=null) {
  const deseadas=valoresInterfaz(), g=generacion;
  if (!titular) return Promise.reject(new Error('Inicia sesión para guardar estos ajustes en tu cuenta.'));
  const guardar=async () => {
    if (g!==generacion) throw new Error('La sesión cambió; vuelve a abrir los ajustes.');
    if (!cargada) {
      const actual=await pedir('/preferencias-interfaz');
      if (g!==generacion) throw new Error('La sesión cambió.');
      revision=actual.revision ?? 0; confirmadas={...actual.preferencias,...normalizarColores(actual.preferencias)}; cargada=true;
    }
    const cambios=Object.fromEntries(Object.entries(deseadas).filter(([k,v]) => confirmadas[k]!==v && (!campos || campos.includes(k))));
    if (!Object.keys(cambios).length) return;
    let resultado;
    try { resultado=await pedir('/preferencias-interfaz',{metodo:'PATCH',cuerpo:{cambios,revision}}); }
    catch(e) {
      if (e.estado!==409 || g!==generacion) throw e;
      const actual=await pedir('/preferencias-interfaz');
      if (g!==generacion) throw new Error('La sesión cambió.');
      resultado=await pedir('/preferencias-interfaz',{metodo:'PATCH',cuerpo:{cambios,revision:actual.revision}});
    }
    if (g!==generacion) return;
    revision=resultado.revision; confirmadas={...confirmadas,...resultado.preferencias,...normalizarColores(resultado.preferencias)};
    recordarAparienciaLocal(confirmadas);
  };
  const tarea=cola.catch(()=>{}).then(guardar);
  cola=tarea;
  return tarea;
}

export function guardarTemaDeCuenta(tema) {
  preferencias.elegirTema(tema);
  if (!titular) { recordarAparienciaLocal(valoresInterfaz()); return Promise.resolve(); }
  return guardarInterfaz(['tema']);
}
