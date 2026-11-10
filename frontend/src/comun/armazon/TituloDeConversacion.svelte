<!-- Títulos nuevos y antiguos comparten la misma lectura matemática segura. -->
<script>
  import { renderizar } from '../../nucleo/formato/notacion.js';
  let { titulo = '' } = $props();
  // Conservar las marcas originales cuando son texto literal o notación rota.
  // Los títulos antiguos también pueden envolver $...$ en backticks.
  const marcas = /(?<!\\)\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|(?<!\\)\$([^$\n]+?)\$|`([^`\n]+)`/g;
  function esProsa(valor) {
    if (/\\[a-zA-Z]+/.test(valor)) return false;
    const palabras = valor.match(/[a-záéíóúñ]{2,}/gi) ?? [];
    return palabras.some(p => !/^(?:lim|sin|cos|tan|sen|tg|ctg|ln|log|exp|sqrt|infty|arcsen|arctg)$/i.test(p));
  }
  function prosaConFunciones(texto) {
    // Reconocer f(x)=... dentro de una frase histórica, sin convertir la
    // instrucción «y explícame...» en variables matemáticas.
    const funcion = /\b[a-zA-Z]\(\s*[a-zA-Z]\s*\)\s*=\s*(?:(?:\\[a-zA-Z]+|(?:sqrt|sin|cos|tan|sen|ln|log|exp)\b|[a-zA-Z](?![a-zA-Záéíóúñ])|\d+(?:\.\d+)?|[+\-*/^_(){}=.,π∞²³⁴⁵⁶⁷⁸⁹⁰])\s*)+/g;
    const salida = [];
    let desde = 0;
    for (const marca of texto.matchAll(funcion)) {
      // Una barra invertida puede ser el escape de un dólar literal.
      if (marca.index > 0 && /[$\\]/.test(texto[marca.index - 1])) continue;
      let valor = marca[0].trim();
      if (/\s+y$/.test(valor) && !/[+\-*/=^]\s+y$/.test(valor)) valor = valor.replace(/\s+y$/, '');
      if (!valor.split('=')[1]?.trim() || /[+\-*/^_]$/.test(valor)) continue;
      const resultado = renderizar(valor);
      if (!resultado.html) continue;
      if (marca.index > desde) salida.push({tipo:'texto',valor:texto.slice(desde,marca.index)});
      salida.push({tipo:'formula',valor,...resultado});
      desde = marca.index + valor.length;
    }
    if (desde < texto.length) salida.push({tipo:'texto',valor:texto.slice(desde)});
    return salida;
  }
  function separar(texto) {
    const salida = [];
    let desde = 0;
    for (const marca of texto.matchAll(marcas)) {
      if (marca.index > desde) salida.push(...prosaConFunciones(texto.slice(desde,marca.index)));
      let valor = marca.slice(1).find(v => v !== undefined);
      const codigo = marca[5] !== undefined;
      if (codigo) {
        const interior = separar(valor);
        if (interior.length === 1 && interior[0].tipo === 'formula') valor = interior[0].valor;
      }
      const matematica = !esProsa(valor) && (!codigo || /[=^_]|\\(?:frac|lim|sqrt|int|sum)\b/.test(valor) || valor !== marca[5]);
      const resultado = matematica ? renderizar(valor) : {html:null};
      salida.push(resultado.html ? {tipo:'formula',valor,...resultado} : {tipo:'texto',valor:marca[0]});
      desde = marca.index + marca[0].length;
    }
    if (desde < texto.length) salida.push(...prosaConFunciones(texto.slice(desde)));
    return salida;
  }
  const partes = $derived.by(() => {
    const texto = String(titulo ?? '');
    let piezas = separar(texto);
    // Algunos títulos históricos guardaron la expresión sin delimitadores.
    // Sólo reconocer una expresión completa explícita, nunca una frase normal.
    if (!piezas.some(p => p.tipo === 'formula') && !texto.includes('…') &&
        /^\\(?:lim|frac|sqrt|int|sum)\b/.test(texto.trim())) {
      piezas = [{tipo:'formula',valor:texto.trim()}];
    }
    return piezas.map(p => p.tipo === 'formula' ? {...p,...renderizar(p.valor)} : p);
  });
</script>

<span class="titulo" title={titulo}>
  {#each partes as parte, i (i)}
    {#if parte.tipo === 'formula' && parte.html}
      <span class="matematica" role="math" aria-label={parte.valor}>{@html parte.html}</span>
    {:else}{parte.valor}{/if}
  {/each}
</span>

<style>
  .titulo { min-inline-size:0; line-height:1.7; }
  .matematica { display:inline-block; vertical-align:middle; }
  .matematica :global(.katex) { font-size:1em; color:inherit; }
</style>
