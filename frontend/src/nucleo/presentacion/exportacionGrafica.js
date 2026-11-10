/** Operaciones geométricas y editoriales de la exportación de gráficas. */

const NS_SVG = 'http://www.w3.org/2000/svg';

/**
 * Amplía una caja sin recortarla hasta que una unidad de X y una de Y tengan
 * el mismo tamaño físico dentro del rectángulo disponible.
 */
export function ajustarCajaAProporcion(caja, anchoPixeles, altoPixeles) {
  const [izquierda, arriba, derecha, abajo] = caja;
  const ancho = Math.abs(derecha - izquierda);
  const alto = Math.abs(arriba - abajo);
  const proporcionLienzo = Math.max(1, Number(anchoPixeles) || 1)
    / Math.max(1, Number(altoPixeles) || 1);
  const proporcionMundo = ancho / alto;
  const centroX = (izquierda + derecha) / 2;
  const centroY = (arriba + abajo) / 2;

  if (proporcionMundo < proporcionLienzo) {
    const medioAncho = (alto * proporcionLienzo) / 2;
    return [centroX - medioAncho, arriba, centroX + medioAncho, abajo];
  }

  const medioAlto = (ancho / proporcionLienzo) / 2;
  return [izquierda, centroY + medioAlto, derecha, centroY - medioAlto];
}

/**
 * Da fondo explícito al SVG. Sin este rectángulo el SVG es transparente y un
 * visor puede convertir una gráfica oscura en papel blanco al exportarla.
 */
export function agregarFondoDeTema(svg, ancho, alto, color) {
  const fondo = document.createElementNS(NS_SVG, 'rect');
  fondo.setAttribute('data-fondo-tema', 'didaxia');
  fondo.setAttribute('x', '0');
  fondo.setAttribute('y', '0');
  fondo.setAttribute('width', String(ancho));
  fondo.setAttribute('height', String(alto));
  fondo.setAttribute('fill', color || '#ffffff');
  svg.insertBefore(fondo, svg.firstChild);
  return fondo;
}

/** Reproduce las explicaciones visibles en la esquina superior izquierda del SVG.
 * Usa texto SVG nativo para que PNG, JPG, HTML y la impresión PDF conserven
 * las notas sin depender de foreignObject ni de una fuente externa de KaTeX.
 */
export function agregarNotasDeAnalisis(svg, ancho, alto, notas, colores = {}) {
  if (!notas?.length) return null;
  const crear = (tipo, atributos = {}, texto = '') => {
    const nodo = document.createElementNS(NS_SVG, tipo);
    for (const [clave, valor] of Object.entries(atributos)) nodo.setAttribute(clave, String(valor));
    nodo.textContent = texto;
    return nodo;
  };
  const grupo = crear('g', { 'data-notas-analisis': 'didaxia' });
  const margen = 16;
  const anchoTarjeta = Math.min(400, Math.max(160, ancho - 2 * margen));
  const maximoCaracteres = Math.max(18, Math.floor((anchoTarjeta - 28) / 7));
  const partir = (linea) => {
    const palabras = String(linea).split(/\s+/);
    const renglones = [];
    let actual = '';
    for (const palabra of palabras) {
      if (actual && `${actual} ${palabra}`.length > maximoCaracteres) {
        renglones.push(actual);
        actual = palabra;
      } else actual = actual ? `${actual} ${palabra}` : palabra;
    }
    if (actual) renglones.push(actual);
    return renglones;
  };
  let arriba = margen;
  for (const nota of notas) {
    const lineas = (nota.lineas ?? []).flatMap(partir);
    const altura = 38 + lineas.length * 17;
    if (arriba + altura > alto - margen) break;
    grupo.appendChild(crear('rect', {
      x: margen, y: arriba, width: anchoTarjeta, height: altura, rx: 10,
      fill: colores.fondo || '#ffffff',
      stroke: colores.borde || '#cbd5e1', 'stroke-width': 1.5
    }));
    grupo.appendChild(crear('rect', {
      x: margen, y: arriba, width: 4, height: altura, rx: 2,
      fill: colores.acento || '#a64b0a'
    }));
    grupo.appendChild(crear('text', {
      x: margen + 14, y: arriba + 22, fill: colores.acento || '#a64b0a',
      'font-family': 'Arial, sans-serif', 'font-size': 14, 'font-weight': 700
    }, nota.titulo));
    lineas.forEach((linea, indice) => grupo.appendChild(crear('text', {
      x: margen + 14, y: arriba + 42 + indice * 17,
      fill: colores.texto || '#1f2937',
      'font-family': 'Arial, sans-serif', 'font-size': 12
    }, linea)));
    arriba += altura + 10;
  }
  svg.appendChild(grupo);
  return grupo;
}
