/** Solicitar una descarga no permite saber si el SO llegó a guardarla.
 * Mantener el enlace y ofrecer apertura/compartir evita un fallo silencioso.
 */
export const ARCHIVO_DISPONIBLE = 'didaxia:archivo-disponible';

export function descargarBlob(blob, nombre, {
  documento = document, urls = URL, esperaRevocacion = 60000,
  navegador = globalThis.navigator,
} = {}) {
  const enlace = documento.createElement('a');
  const temporal = urls.createObjectURL(blob);
  let liberado = false;
  let temporizador;
  const liberar = () => {
    if (liberado) return;
    liberado = true;
    clearTimeout(temporizador);
    enlace.remove();
    urls.revokeObjectURL(temporal);
  };
  const avisar = compartirRequerido => {
    if (documento === globalThis.document) globalThis.dispatchEvent?.(
      new CustomEvent(ARCHIVO_DISPONIBLE,{detail:{blob,nombre,compartirRequerido}})
    );
  };
  function directa() {
    enlace.href = temporal;
    enlace.download = nombre;
    enlace.hidden = true;
    enlace.rel = 'noopener noreferrer';
    documento.body.appendChild(enlace);
    enlace.click();
    temporizador = setTimeout(liberar, Math.max(60000, esperaRevocacion));
  }
  let finalizada = Promise.resolve();
  try {
    const archivo = new File([blob],nombre,{type:blob.type});
    let comparte = false;
    try { comparte = Boolean(navegador?.share && navegador?.canShare?.({files:[archivo]})); }
    catch { comparte = false; }
    // Async graph/PDF generation may have consumed the original user gesture.
    // Keep the real file ready and request a fresh tap instead of a blocked share.
    if (comparte && navegador.userActivation?.isActive === false) {
      avisar(true);
      liberar();
    } else if (comparte) {
      avisar(false);
      let peticion;
      try { peticion = navegador.share({files:[archivo],title:'Archivo de DidaxIa'}); }
      catch (error) { peticion = Promise.reject(error); }
      finalizada = Promise.resolve(peticion).then(liberar,error => {
        if (error?.name === 'AbortError') liberar();
        else { try { directa(); } catch { liberar(); avisar(true); } }
      });
    } else {
      directa();
      avisar(false);
    }
  } catch (error) { liberar(); throw error; }
  return Object.freeze({nombre,liberar,finalizada});
}
