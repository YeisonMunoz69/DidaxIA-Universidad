/** La lectura y el análisis no bloquean la animación ni la interfaz. */
export function importarPresentacion(archivo) {
  if (archivo.size > 15_000_000) return Promise.reject(new Error('El archivo supera 15 MB. Reduce las imágenes o importa una copia más pequeña.'));
  return new Promise((resolve, reject) => {
    const lector = new Worker(new URL('./importarPresentacion.worker.js', import.meta.url), { type: 'module' });
    const cerrar = () => { clearTimeout(reloj); lector.terminate(); };
    const reloj = setTimeout(() => { cerrar(); reject(new Error('La lectura tardó demasiado. Revisa el archivo e intenta importar de nuevo.')); }, 30000);
    lector.onmessage = ({ data }) => { cerrar(); data.error ? reject(new Error(data.error)) : resolve(data.contenido); };
    lector.onerror = () => { cerrar(); reject(new Error('No se pudo preparar la importación. Recarga la página e intenta de nuevo.')); };
    lector.postMessage(archivo);
  });
}
