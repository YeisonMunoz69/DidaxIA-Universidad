
export function fragmentosMarkdown(texto = '') {
  const fuente = String(texto);
  const patron = /\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*/g;
  const salida = [];
  let desde = 0;
  for (const marca of fuente.matchAll(patron)) {
    if (marca.index > desde) salida.push({ tipo: 'texto', valor: fuente.slice(desde, marca.index) });
    if (marca[1] !== undefined) {
      const codigoFuerte = marca[1].match(/^`([^`]+)`$/);
      salida.push({
        tipo: codigoFuerte ? 'fuerte_codigo' : 'fuerte',
        valor: codigoFuerte ? codigoFuerte[1] : marca[1]
      });
    }
    else if (marca[2] !== undefined) salida.push({ tipo: 'codigo', valor: marca[2] });
    else salida.push({ tipo: 'enfasis', valor: marca[3] });
    desde = marca.index + marca[0].length;
  }
  if (desde < fuente.length) salida.push({ tipo: 'texto', valor: fuente.slice(desde) });
  return salida;
}

function celdas(linea) {
  return linea.trim().replace(/^\||\|$/g, '').split('|').map((celda) => celda.trim());
}

function esSeparadorDeTabla(linea) {
  return celdas(linea).every((celda) => /^:?-{3,}:?$/.test(celda));
}

function iniciaBloque(linea) {
  return /^(#{1,4})\s+|^\s*([-*])\s+|^\s*\d+[.)]\s+|^\s*\|/.test(linea) || /^\s*---+\s*$/.test(linea);
}

export function bloquesMarkdown(texto = '') {
  const lineas = String(texto).replace(/\r\n?/g, '\n').split('\n');
  const bloques = [];
  let i = 0;

  while (i < lineas.length) {
    const linea = lineas[i];
    if (!linea.trim()) { i += 1; continue; }

    const titulo = linea.match(/^(#{1,4})\s+(.+)$/);
    if (titulo) {
      bloques.push({ tipo: 'titulo', nivel: titulo[1].length, contenido: fragmentosMarkdown(titulo[2]) });
      i += 1;
      continue;
    }
    if (/^\s*---+\s*$/.test(linea)) {
      bloques.push({ tipo: 'separador' });
      i += 1;
      continue;
    }
    if (/^\s*\|/.test(linea)) {
      const filas = [];
      while (i < lineas.length && /^\s*\|/.test(lineas[i])) {
        filas.push(celdas(lineas[i]));
        i += 1;
      }
      const cabecera = filas.shift() ?? [];
      if (filas.length && esSeparadorDeTabla(`|${filas[0].join('|')}|`)) filas.shift();
      bloques.push({ tipo: 'tabla', cabecera, filas });
      continue;
    }

    const lista = linea.match(/^\s*([-*]|\d+[.)])\s+(.+)$/);
    if (lista) {
      const ordenada = /^\d/.test(lista[1]);
      const items = [];
      while (i < lineas.length) {
        const item = lineas[i].match(/^\s*([-*]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[1]) !== ordenada) break;
        const contenido = [item[2].trim()];
        i += 1;
        while (i < lineas.length && /^\s{2,}\S/.test(lineas[i])) {
          contenido.push(lineas[i].trim());
          i += 1;
        }
        items.push(fragmentosMarkdown(contenido.join(' ')));
      }
      bloques.push({ tipo: 'lista', ordenada, items });
      continue;
    }

    const parrafo = [linea.trim()];
    i += 1;
    while (i < lineas.length && lineas[i].trim() && !iniciaBloque(lineas[i])) {
      parrafo.push(lineas[i].trim());
      i += 1;
    }
    bloques.push({ tipo: 'parrafo', contenido: fragmentosMarkdown(parrafo.join(' ')) });
  }
  return bloques;
}
