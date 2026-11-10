/** Cuenta también las imágenes repetidas: cada aparición viaja en el JSON. */
export const MAX_BYTES_IMAGENES_ENCUESTA = 8_000_000;

export function resumenImagenesEncuesta(contenido) {
 let bytes=0, cantidad=0, sinDescripcion=0;
 for(const pagina of contenido?.paginas??[])for(const bloque of [pagina,...pagina.preguntas??[]]){
  for(const imagen of bloque.imagenes??[]){
   cantidad++;
   if(!imagen.alt?.trim())sinDescripcion++;
   const base64=imagen.src?.split(',')[1]??'';
   bytes+=Math.max(0,Math.floor(base64.length*3/4)-(base64.endsWith('==')?2:base64.endsWith('=')?1:0));
  }
 }
 return {bytes,cantidad,sinDescripcion};
}

export function comprobarPesoEncuesta(recurso) {
 if(recurso.tipo!=='encuesta')return;
 if(resumenImagenesEncuesta(recurso.contenido).bytes>MAX_BYTES_IMAGENES_ENCUESTA){
  throw new Error('Las imágenes de la encuesta superan 8 MB. Reduce su tamaño o quita alguna imagen antes de guardar. Tus cambios siguen en el editor.');
 }
}
