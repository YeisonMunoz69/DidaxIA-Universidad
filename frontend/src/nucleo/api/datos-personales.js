import { pedir, pedirArchivo, pedirBinario } from './cliente.js';

const RUTA = '/datos-personales';

export async function consultar({ señal } = {}) {
  return pedir(RUTA, { señal });
}

export async function exportar({ señal } = {}) {
  return pedir(`${RUTA}/exportar`, { señal });
}

export async function consultarFoto({ señal } = {}) {
  try {
    const archivo = await pedirArchivo(`${RUTA}/foto`, { tipo: 'image/webp', señal });
    return URL.createObjectURL(archivo);
  } catch (error) {
    if (error?.estado === 404) return null;
    throw error;
  }
}

export async function guardarFoto(archivo, { señal } = {}) {
  return pedirBinario(`${RUTA}/foto`, {
    contenido: archivo,
    tipo: archivo?.type || 'application/octet-stream',
    metodo: 'PUT',
    señal
  });
}

export async function retirarFoto({ señal } = {}) {
  return pedir(`${RUTA}/foto`, { metodo: 'DELETE', señal });
}


export function descargar(exportacion, nombre = 'mis-datos.json') {
  const blob = new Blob([JSON.stringify(exportacion, null, 2)], {
    type: 'application/json'
  });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}
