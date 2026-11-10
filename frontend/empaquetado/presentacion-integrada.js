import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const fuente = new URL('../publico/presentaciones/editor.html', import.meta.url);
export function prepararPresentacionIntegrada(html) {
  function datos(id) {
    const patron=new RegExp(`(<script id="${id}" type="application/json">)([\\s\\S]*?)(</script>)`);
    const hallado=html.match(patron);
    if(!hallado)throw new Error(`Falta ${id} en el editor de presentaciones.`);
    return { patron, texto:hallado[2], objeto:JSON.parse(hallado[2]) };
  }
  const pdf=datos('didaxia-pdf-assets'), base=datos('didaxia-data');
  const nombrePdf=`exportador-pdf-${createHash('sha256').update(pdf.texto).digest('hex').slice(0,16)}.json`;
  // El contenido real llega por el canal verificado del iframe. La base completa
  // sigue disponible en editor.html y los HTML descargados siguen autónomos.
  const minima={...base.objeto,slides:[{...base.objeto.slides[0],items:[],note:''}]};
  const sustituir=(patron,objeto)=>{html=html.replace(patron,(_todo,inicio,_datos,fin)=>inicio+JSON.stringify(objeto).replaceAll('<','\\u003c')+fin);};
  sustituir(pdf.patron,{url:`/presentaciones/${nombrePdf}`});
  sustituir(base.patron,minima);
  return {html,nombrePdf,pdf:pdf.texto};
}

export function presentacionIntegrada() {
  let artefactos;
  const obtener=()=>artefactos??=prepararPresentacionIntegrada(readFileSync(fuente,'utf8'));
  return {
    name:'presentacion-integrada-ligera',
    generateBundle() {
      const a=obtener();
      this.emitFile({type:'asset',fileName:'presentaciones/editor-integrado.html',source:a.html});
      this.emitFile({type:'asset',fileName:`presentaciones/${a.nombrePdf}`,source:a.pdf});
    },
    configureServer(servidor) {
      servidor.middlewares.use((peticion,respuesta,siguiente)=>{
        const camino=(peticion.url??'').split('?')[0];
        if(!camino.startsWith('/presentaciones/'))return siguiente();
        const a=obtener();
        const esHtml=camino==='/presentaciones/editor-integrado.html';
        if(!esHtml&&camino!==`/presentaciones/${a.nombrePdf}`)return siguiente();
        respuesta.setHeader('Content-Type',esHtml?'text/html; charset=utf-8':'application/json; charset=utf-8');
        respuesta.end(esHtml?a.html:a.pdf);
      });
    }
  };
}
