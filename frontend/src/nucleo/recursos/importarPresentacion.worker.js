import { leerPresentacion } from './leerPresentacion.js';
self.onmessage = async ({ data: archivo }) => {
  try {
    const contenido = leerPresentacion(await archivo.text(), archivo.name);
    self.postMessage({ contenido });
  } catch (error) {
    self.postMessage({ error: error.message || 'No se pudo leer el archivo.' });
  }
};
