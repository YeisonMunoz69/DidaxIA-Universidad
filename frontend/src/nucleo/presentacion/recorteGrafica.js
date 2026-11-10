/** Recorta segmentos ya muestreados en píxeles; no altera la función ni su dominio. */
export function recortarTrazado(puntos, ancho, alto) {
  const caja = [-2 * ancho, -2 * alto, 3 * ancho, 3 * alto];
  let anterior = null;
  let extremo = null;
  let trazo = '';
  for (const punto of puntos) {
    const actual = punto.slice(-2);
    if (!actual.every(Number.isFinite)) {
      anterior = null; extremo = null;
      continue;
    }
    if (anterior) {
      const segmento = recortarSegmento(anterior, actual, caja);
      if (segmento) {
        const [inicio, fin] = segmento;
        if (!extremo || inicio[0] !== extremo[0] || inicio[1] !== extremo[1]) trazo += ` M ${inicio[0]} ${inicio[1]}`;
        trazo += ` L ${fin[0]} ${fin[1]}`;
        extremo = fin;
      } else extremo = null;
    }
    anterior = actual;
  }
  return trazo;
}

function recortarSegmento(a, b, caja) {
  // Normalizar evita desbordar al restar coordenadas próximas a ±1e308.
  const escala = Math.max(1, ...a.map(Math.abs), ...b.map(Math.abs), ...caja.map(Math.abs));
  const p = a.map(v => v / escala);
  const q = b.map(v => v / escala);
  let entrada = 0, salida = 1;
  let bordeEntrada = null, bordeSalida = null;
  for (let eje = 0; eje < 2; eje++) {
    const d = q[eje] - p[eje];
    const menor = caja[eje] / escala, mayor = caja[eje + 2] / escala;
    if (d === 0) { if (p[eje] < menor || p[eje] > mayor) return null; continue; }
    const t1 = (menor - p[eje]) / d, t2 = (mayor - p[eje]) / d;
    const tEntrada = Math.min(t1, t2), tSalida = Math.max(t1, t2);
    if (tEntrada > entrada) { entrada = tEntrada; bordeEntrada = [eje, d > 0 ? caja[eje] : caja[eje + 2]]; }
    if (tSalida < salida) { salida = tSalida; bordeSalida = [eje, d > 0 ? caja[eje + 2] : caja[eje]]; }
    if (entrada > salida) return null;
  }
  const interpolar = (t, borde) => {
    if (!borde && t === 0) return a;
    if (!borde && t === 1) return b;
    const resultado = p.map((v, eje) => Math.max(caja[eje], Math.min(caja[eje + 2], ((1 - t) * v + t * q[eje]) * escala)));
    if (borde) resultado[borde[0]] = borde[1];
    return resultado;
  };
  return [interpolar(entrada, bordeEntrada), interpolar(salida, bordeSalida)];
}

/** Usa el ciclo público de actualización de cada curva, sin modificar JSXGraph. */
export function protegerTrazadoSVG(curva) {
  // Las asíntotas pueden producir millones de píxeles fuera del plano.
  // Recortar antes de pintar evita perder el resto del SVG en el navegador.
  // Se conservan los puntos de JSXGraph para su muestreo y detección de saltos.
  const actualizar = curva.updateRenderer;
  curva.updateRenderer = function () {
    const necesitaActualizar = this.needsUpdate;
    actualizar.call(this);
    if (necesitaActualizar && this.board.renderer.type === 'svg' && this.rendNode) {
      this.rendNode.setAttribute('d', recortarTrazado(
        this.points.slice(0, this.numberPoints).map(p => p.scrCoords),
        this.board.canvasWidth, this.board.canvasHeight
      ));
    }
    return this;
  };
  curva.needsUpdate = true;
  curva.updateRenderer();
  return curva;
}
