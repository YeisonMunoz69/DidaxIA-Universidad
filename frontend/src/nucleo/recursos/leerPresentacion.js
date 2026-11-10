/** Extrae únicamente el documento editable. Nunca interpreta el HTML. */
export function leerPresentacion(texto, nombre) {
  let datos = texto;
  if (/\.html?$/i.test(nombre)) {
    datos = null;
    for (const script of texto.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
      const atributos = script[1];
      if (/(?:^|\s)id\s*=\s*(?:"didaxia-data"|'didaxia-data'|didaxia-data(?=\s|$))/i.test(atributos)
          && /(?:^|\s)type\s*=\s*(?:"application\/json"|'application\/json'|application\/json(?=\s|$))/i.test(atributos)) {
        datos = script[2]; break;
      }
    }
    if (datos === null) throw new Error('Este HTML no contiene una presentación DidaxIa. Importa el HTML o JSON exportado desde el editor.');
  }
  let contenido;
  try { contenido = JSON.parse(datos.replace(/^\uFEFF/, '')); }
  catch { throw new Error('No se pudo leer el contenido de la presentación. El archivo JSON está incompleto o no es válido.'); }
  if (!contenido || !Array.isArray(contenido.slides) || contenido.slides.length < 1 || contenido.slides.length > 100) {
    throw new Error('La copia debe contener una presentación de 1 a 100 diapositivas.');
  }
  return contenido;
}
