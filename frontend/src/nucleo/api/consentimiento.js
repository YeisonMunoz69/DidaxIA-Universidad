import { RUTAS, pedir, pedirArchivo, pedirBinario } from './cliente.js';

export const TIPO_DE_EVIDENCIA = 'application/pdf';
export const TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024;

export const DECISIONES = Object.freeze(['otorgado', 'rechazado']);

export async function textoDeVersion(codigo, { señal } = {}) {
  return pedir(RUTAS.textoDeVersion(codigo), { señal });
}

export async function versiones({ señal } = {}) {
  return pedir(RUTAS.versiones, { señal });
}

export function hayVersion(documento) {
  return Boolean(documento && documento.codigo);
}

export async function decidirConjunta(decision, { señal } = {}) {
  return pedir(RUTAS.decisionConjunta, {
    metodo: 'POST',
    cuerpo: { decision },
    señal
  });
}

export async function revocarTitular({ señal } = {}) {
  return pedir(RUTAS.revocarTitular, { metodo: 'POST', señal });
}

export async function revocarAsentimiento({ señal } = {}) {
  return pedir(RUTAS.revocarAsentimiento, { metodo: 'POST', señal });
}

export function motivoParaNoSubir(archivo) {
  if (!archivo) return 'Elige el archivo con la autorización firmada.';
  if (archivo.type !== TIPO_DE_EVIDENCIA) {
    return 'La autorización se recibe en PDF. Ese archivo tiene otro formato.';
  }
  if (!archivo.size) return 'Ese archivo está vacío.';
  if (archivo.size > TAMANO_MAXIMO_BYTES) {
    return 'La autorización no puede pasar de 10 MB.';
  }
  return '';
}

export async function descargarFormatoRepresentante({ señal } = {}) {
  const documento = await pedirArchivo(RUTAS.formatoRepresentante, { señal });
  const direccion = URL.createObjectURL(documento);
  try {
    const enlace = document.createElement('a');
    enlace.href = direccion;
    enlace.download = 'autorizacion-representante-menor.pdf';
    enlace.hidden = true;
    document.body.append(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(direccion);
  }
}

export async function cargarEvidencia(archivo, { señal } = {}) {
  return pedirBinario(RUTAS.evidencia, {
    contenido: archivo,
    tipo: TIPO_DE_EVIDENCIA,
    espera: 90_000,
    señal
  });
}
