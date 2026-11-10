/** Rasterizar elimina metadatos; se conserva suficiente resolución para fórmulas. */
export async function prepararImagenEncuesta(archivo) {
 if(!['image/png','image/jpeg','image/webp'].includes(archivo.type))throw new Error('Usa una imagen PNG, JPEG o WebP.');
 if(archivo.size>12_000_000)throw new Error('El archivo supera 12 MB. Recorta o reduce la captura.');
 const url=URL.createObjectURL(archivo);
 try{
  const imagen=new Image();imagen.src=url;await imagen.decode();
  if(imagen.naturalWidth*imagen.naturalHeight>40_000_000)throw new Error('La imagen es demasiado grande. Divídela en varias capturas.');
  const escala=Math.min(1,2200/Math.max(imagen.naturalWidth,imagen.naturalHeight));
  const lienzo=document.createElement('canvas');lienzo.width=Math.max(1,Math.round(imagen.naturalWidth*escala));lienzo.height=Math.max(1,Math.round(imagen.naturalHeight*escala));
  const contexto=lienzo.getContext('2d');if(!contexto)throw new Error('No se pudo preparar la imagen.');
  contexto.drawImage(imagen,0,0,lienzo.width,lienzo.height);
  const src=lienzo.toDataURL('image/webp',.92);
  if(src.length>2_000_000)throw new Error('La imagen preparada supera 1,5 MB. Divídela o recórtala.');
  return {src,alt:'',pie:''};
 }finally{URL.revokeObjectURL(url);}
}
