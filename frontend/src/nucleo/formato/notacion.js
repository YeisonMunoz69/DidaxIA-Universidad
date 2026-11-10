/**
 * Envoltura de KaTeX con soporte para macros de cálculo y funciones en español.
 *
 * Recibe la expresión y la renderiza de forma accesible y tipográficamente correcta.
 *
 */
import katex from 'katex';
import { registrarLimpiezaDeLectura } from '../lectura/cache.js';
import 'katex/dist/katex.min.css';

/**
 * Macros matemáticas en español y notaciones estándar de cálculo.
 */
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

// RAM acotada: no vuelve a ejecutar KaTeX al regresar a una fórmula conocida.
// No conserva expresiones al cerrar sesión y no altera el normalizador existente.
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

/**
 * Convierte una expresión en marcado, o declara que no pudo.
 *
 * @param {string} expresion  ya normalizada o expresión matemática
 * @param {{bloque?: boolean, agrandar?: boolean}} opciones
 *   `bloque` para su propia línea. `agrandar` fuerza el tamaño de
 *   `\displaystyle` en una fórmula que va EN LÍNEA —`bloque: false`—: sin
 *   él, KaTeX dibuja `\frac`, `\sum`, `\lim`, etc. en el tamaño comprimido
 *   de «texto corrido», que para una fracción significa numerador y
 *   denominador diminutos en vez de uno claramente encima del otro. No
 *   afecta a `bloque: true`, que ya usa ese tamaño por sí solo.
 * @returns {{html: string, error: null} | {html: null, error: string}}
 */
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
    // Si falló por funciones sin barra invertida o asteriscos de multiplicación,
    // intentar una normalización suave
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

/**
 * Ajustes tipográficos, no algebraicos: no cambia la expresión ni decide si es
 * correcta. Sólo dice a KaTeX que `cos`, `sin`, `sen`, etc. son nombres de
 * funciones y que `*` es un signo de multiplicación. KaTeX acepta `cos(x)` sin
 * lanzar error, pero lo pinta como tres variables c·o·s; por eso hacerlo sólo
 * en el `catch` era demasiado tarde.
 */
export function normalizarParaPresentacion(expresion) {
  // El normalizador del servidor conserva superíndices Unicode como ^(4).
  // KaTeX interpreta esa forma como exponente «(» y deja «4)» en la base.
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

/** Las respuestas históricas guardaron divisiones dentro de paréntesis. */
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

/**
 * Traduce la barra de una división escrita en forma corriente a una fracción
 * tipográfica. Se limita deliberadamente al nivel exterior: una barra dentro
 * de paréntesis o llaves puede pertenecer a otro subproblema y no se toca sin
 * un analizador algebraico. Los límites del numerador y denominador son los
 * operadores aditivos del mismo nivel, de modo que
 * `x'/sqrt(x+x^2) + 2*x^3` se lee como
 * `\\frac{x'}{\\sqrt{x+x^2}} + 2\\cdot x^3`.
 */
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

/**
 * Convierte `sqrt(contenido)` a `\\sqrt{contenido}` respetando paréntesis
 * anidados. No usa una expresión regular para capturar el contenido: cerraría
 * en el primer `)` y rompería casos como `sqrt(x*(x+1))`.
 */
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

/**
 * La marca con la que el estudiante o tutor dice «esto es notación»: `$…$`, `$$...$$`, `\(...\)`, `\[...\]`.
 */
const MARCA_DE_NOTACION = /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\(.+?\\\)|(\$[^$\n]+\$)/g;

/**
 * Parte lo que hay escrito en trozos marcados como notación y trozos que no.
 *
 * @param {string} texto
 * @returns {{marcado: boolean, valor: string}[]}
 */
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

/**
 * Parte un texto en trozos: prosa, énfasis, código y notación.
 *
 * Soporta delimitadores KaTeX/LaTeX estándar:
 * - `$$...$$` y `\[...\]` (fórmulas en bloque)
 * - `$...$` y `\(...\)` (fórmulas en línea)
 * - `**...**` (énfasis)
 * - `*...*` (matiz)
 * - `` `...` `` (código o fórmulas dentro de backticks)
 *
 * @param {string} texto
 * @returns {{tipo: 'texto'|'enfasis'|'matiz'|'codigo'|'formula', valor: string}[]}
 */
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
      // Si dentro de los backticks hay notación matemática evidente (frac, sqrt, etc.), se interpreta como fórmula
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
