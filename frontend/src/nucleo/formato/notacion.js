import katex from 'katex';
import { registrarLimpiezaDeLectura } from '../lectura/cache.js';
import 'katex/dist/katex.min.css';

export const MACROS_CALCULO = {
  '\\sen': '\\operatorname{sen}',
  '\\tg': '\\operatorname{tg}',
  '\\ctg': '\\operatorname{ctg}',
  '\\arctg': '\\operatorname{arctg}',
  '\\arcsen': '\\operatorname{arcsen}',
  '\\arcsec': '\\operatorname{arcsec}',
  '\\arccsc': '\\operatorname{arccsc}',
  '\\arcctg': '\\operatorname{arcctg}',
  '\\senh': '\\operatorname{senh}',
  '\\tgh': '\\operatorname{tgh}',
  '\\ctgh': '\\operatorname{ctgh}',
  '\\dif': '\\mathrm{d}',
  '\\dx': '\\mathrm{d}x',
  '\\dy': '\\mathrm{d}y',
  '\\dt': '\\mathrm{d}t',
  '\\du': '\\mathrm{d}u',
  '\\dv': '\\mathrm{d}v',
  '\\d': '\\mathrm{d}',
  '\\R': '\\mathbb{R}',
  '\\N': '\\mathbb{N}',
  '\\Z': '\\mathbb{Z}'
};

const notaciones = new Map();
const LIMITE_NOTACIONES = 2048;
registrarLimpiezaDeLectura(() => notaciones.clear());
export function renderizar(expresion, { bloque = false, agrandar = false } = {}) {
  if (typeof expresion !== 'string' || !expresion.trim()) {
    return renderizarSinCache(expresion, { bloque, agrandar });
  }
  const clave = JSON.stringify([expresion, Boolean(bloque), Boolean(agrandar)]);
  if (notaciones.has(clave)) {
    const resultado = notaciones.get(clave);
    notaciones.delete(clave); notaciones.set(clave, resultado);
    return { ...resultado };
  }
  const resultado = renderizarSinCache(expresion, { bloque, agrandar });
  notaciones.set(clave, { ...resultado });
  if (notaciones.size > LIMITE_NOTACIONES) notaciones.delete(notaciones.keys().next().value);
  return resultado;
}

function renderizarSinCache(expresion, { bloque = false, agrandar = false } = {}) {
  if (typeof expresion !== 'string' || !expresion.trim()) {
    return { html: null, error: 'expresión vacía' };
  }
  let limpia = normalizarParaPresentacion(expresion.trim());
  if (agrandar && !bloque) limpia = `\\displaystyle ${limpia}`;
  try {
    return {
      html: katex.renderToString(limpia, {
        displayMode: bloque,
        throwOnError: true,
        maxExpand: 1000,
        strict: false,
        macros: MACROS_CALCULO,
        output: 'html'
      }),
      error: null
    };
  } catch (e) {
    try {
      const normalizada = limpia
        .replace(/\bsen\b/g, '\\operatorname{sen}')
        .replace(/\btg\b/g, '\\operatorname{tg}')
        .replace(/\bctg\b/g, '\\operatorname{ctg}')
        .replace(/\barcsen\b/g, '\\operatorname{arcsen}')
        .replace(/\barctg\b/g, '\\operatorname{arctg}')
        .replace(/\*/g, ' \\cdot ');

      return {
        html: katex.renderToString(normalizada, {
          displayMode: bloque,
          throwOnError: true,
          maxExpand: 1000,
          strict: false,
          macros: MACROS_CALCULO,
          output: 'html'
        }),
        error: null
      };
    } catch {
      return { html: null, error: e?.message ?? 'no se pudo interpretar la notación' };
    }
  }
}

export function normalizarParaPresentacion(expresion) {
  const potencias = expresion.replace(/\^\(([^()]+)\)/g, '^{$1}');
  const limites = potencias.replace(
    /\blim\s+([a-zA-Z])\s*(?:->|→)\s*([^\s()]+)/g,
    (_, variable, destino) => `\\lim_{${variable}\\to ${destino.replace(/\boo\b/g, '\\infty')}}`
  );
  return convertirRaicesAscii(convertirDivisionesEnGrupos(limites))
    .replace(/\\(sen|tg|ctg|arcsen|arctg)\b/g, (_, nombre) => `\\operatorname{${nombre}}`)
    .replace(/(?<![\\\w{])\b(sen|tg|ctg|arcsen|arctg)\b/g, (_, nombre) => `\\operatorname{${nombre}}`)
    .replace(/(?<!\\)\b(sin|cos|tan|ln|log|exp)\b/g, '\\$&')
    .replace(/\*/g, ' \\cdot ');
}

function convertirDivisionesEnGrupos(expresion) {
  let salida = '';
  for (let i = 0; i < expresion.length;) {
    if (expresion[i] !== '(') {
      salida += expresion[i++];
      continue;
    }
    let profundidad = 1;
    let fin = i + 1;
    while (fin < expresion.length && profundidad) {
      if (expresion[fin] === '(') profundidad += 1;
      else if (expresion[fin] === ')') profundidad -= 1;
      fin += 1;
    }
    if (profundidad) {
      salida += expresion[i++];
      continue;
    }
    salida += `(${convertirDivisionesEnGrupos(expresion.slice(i + 1, fin - 1))})`;
    i = fin;
  }
  return convertirDivisionAscii(salida);
}

function convertirDivisionAscii(expresion) {
  let profundidad = 0;
  let barra = -1;
  for (let i = 0; i < expresion.length; i += 1) {
    const caracter = expresion[i];
    if (caracter === '\\') {
      i += 1;
      continue;
    }
    if ('([{'.includes(caracter)) profundidad += 1;
    else if (')]}'.includes(caracter)) profundidad = Math.max(0, profundidad - 1);
    else if (caracter === '/' && profundidad === 0) {
      barra = i;
      break;
    }
  }
  if (barra < 0) return expresion;

  const esLimite = (caracter) => '+-=,;'.includes(caracter);
  let inicio = 0;
  profundidad = 0;
  for (let i = barra - 1; i >= 0; i -= 1) {
    const caracter = expresion[i];
    if (')]}'.includes(caracter)) profundidad += 1;
    else if ('([{'.includes(caracter)) profundidad = Math.max(0, profundidad - 1);
    else if (profundidad === 0 && esLimite(caracter)) {
      inicio = i + 1;
      break;
    }
  }

  let fin = expresion.length;
  profundidad = 0;
  for (let i = barra + 1; i < expresion.length; i += 1) {
    const caracter = expresion[i];
    if (caracter === '\\') {
      i += 1;
      continue;
    }
    if ('([{'.includes(caracter)) profundidad += 1;
    else if (')]}'.includes(caracter)) profundidad = Math.max(0, profundidad - 1);
    else if (profundidad === 0 && esLimite(caracter)) {
      fin = i;
      break;
    }
  }

  const numerador = expresion.slice(inicio, barra).trim();
  const denominador = expresion.slice(barra + 1, fin).trim();
  if (!numerador || !denominador) return expresion;
  return `${expresion.slice(0, inicio)}\\frac{${numerador}}{${denominador}}${expresion.slice(fin)}`;
}

function convertirRaicesAscii(expresion) {
  let salida = '';
  for (let i = 0; i < expresion.length;) {
    const resto = expresion.slice(i);
    const encontrada = /^sqrt\s*\(/.exec(resto);
    const pegadaAIdentificador = i > 0 && /[\\\w]/.test(expresion[i - 1]);
    if (!encontrada || pegadaAIdentificador) {
      salida += expresion[i++];
      continue;
    }
    const abre = i + encontrada[0].lastIndexOf('(');
    let profundidad = 1;
    let cierra = abre + 1;
    for (; cierra < expresion.length && profundidad; cierra += 1) {
      if (expresion[cierra] === '(') profundidad += 1;
      else if (expresion[cierra] === ')') profundidad -= 1;
    }
    if (profundidad !== 0) {
      salida += expresion[i++];
      continue;
    }
    const interior = expresion.slice(abre + 1, cierra - 1);
    salida += `\\sqrt{${convertirRaicesAscii(interior)}}`;
    i = cierra;
  }
  return salida;
}

const MARCA_DE_NOTACION = /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\(.+?\\\)|(\$[^$\n]+\$)/g;

export function segmentarNotacion(texto) {
  const fuente = String(texto ?? '');
  const salida = [];
  let desde = 0;
  for (const m of fuente.matchAll(MARCA_DE_NOTACION)) {
    if (m.index > desde) {
      salida.push({ marcado: false, valor: fuente.slice(desde, m.index) });
    }
    salida.push({ marcado: true, valor: m[0] });
    desde = m.index + m[0].length;
  }
  if (desde < fuente.length) {
    salida.push({ marcado: false, valor: fuente.slice(desde) });
  }
  return salida;
}

export function trozos(texto) {
  const fuente = String(texto ?? '');
  const marca =
    /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$|\*\*((?:[^*\n]|\n(?!\n))+?)\*\*|`([^`\n]+)`|\*([^*\n]+)\*/g;
  const salida = [];
  let desde = 0;

  for (const m of fuente.matchAll(marca)) {
    if (m.index > desde) {
      salida.push({ tipo: 'texto', valor: fuente.slice(desde, m.index) });
    }
    if (m[1] !== undefined) {
      salida.push({ tipo: 'formula', valor: m[1] });
    } else if (m[2] !== undefined) {
      salida.push({ tipo: 'formula', valor: m[2] });
    } else if (m[3] !== undefined) {
      salida.push({ tipo: 'formula', valor: m[3] });
    } else if (m[4] !== undefined) {
      salida.push({ tipo: 'formula', valor: m[4] });
    } else if (m[5] !== undefined) {
      salida.push({ tipo: 'enfasis', valor: m[5] });
    } else if (m[6] !== undefined) {
      const val = m[6];
      if (/\\(frac|sqrt|cdot|int|sum|lim|partial|sin|cos|tan|sen|ln|log|alpha|beta|theta|pi|infty)|[=^_]/.test(val) && !val.includes('git') && !val.includes('npm')) {
        salida.push({ tipo: 'formula', valor: val });
      } else {
        salida.push({ tipo: 'codigo', valor: val });
      }
    } else {
      salida.push({ tipo: 'matiz', valor: m[7] });
    }
    desde = m.index + m[0].length;
  }
  if (desde < fuente.length) {
    salida.push({ tipo: 'texto', valor: fuente.slice(desde) });
  }
  return salida;
}
