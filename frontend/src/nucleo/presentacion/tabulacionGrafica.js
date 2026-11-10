/** Puntos de lectura, no una nueva escala de la gráfica. */
export function destinoNumerico(texto) {
  if (typeof texto === 'number') return Number.isFinite(texto) ? texto : null;
  const limpio = String(texto ?? '').replace(/\\pi|π/g, 'pi').replace(/\s/g, '');
  if (/^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(limpio)) return Number(limpio);
  const pi = /^([+-]?)pi(?:\/(\d+))?$/.exec(limpio);
  if (pi) return (pi[1] === '-' ? -1 : 1) * Math.PI / Number(pi[2] || 1);
  return null;
}

/** La tabla admite coma colombiana y punto, pero no separadores de miles ambiguos. */
export function leerDecimalDeTabla(texto) {
  const limpio = String(texto ?? '').trim().replace(',', '.');
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(limpio)) return null;
  const valor = Number(limpio);
  return Number.isFinite(valor) ? valor : null;
}

export function mostrarDecimalDeTabla(valor) {
  if (!Number.isFinite(valor)) return '—';
  return String(Number(valor.toPrecision(7))).replace('.', ',');
}

export function elegirAbscisas(desde, hasta, destino = null) {
  const izquierda = Number(desde);
  const derecha = Number(hasta);
  if (!Number.isFinite(izquierda) || !Number.isFinite(derecha) || derecha <= izquierda) return [];
  const a = destinoNumerico(destino);
  if (a !== null && a > izquierda && a < derecha) {
    const pasoIzquierdo = (a - izquierda) / 2;
    const pasoDerecho = (derecha - a) / 2;
    return [
      a - pasoIzquierdo, a - pasoIzquierdo / 10,
      a - pasoIzquierdo / 100, a - pasoIzquierdo / 1000,
      a,
      a + pasoDerecho / 1000, a + pasoDerecho / 100,
      a + pasoDerecho / 10, a + pasoDerecho / 2, a + pasoDerecho
    ];
  }
  return Array.from({ length: 10 }, (_, indice) => izquierda + (derecha - izquierda) * indice / 9);
}

/**
 * Conserva el muestreo explícito de un límite y, para funciones ordinarias,
 * aproxima hasta dos focos visibles (raíz, extremo o discontinuidad). Son
 * abscisas para explorar, no una certificación simbólica de puntos críticos.
 */
export function elegirAbscisasConFocos(desde, hasta, destino = null, evaluadores = []) {
  const base = elegirAbscisas(desde, hasta, destino);
  const destinoTextual = String(destino ?? '').trim().toLowerCase();
  if (/^(?:oo|\+oo|∞|\+∞|infinito|\\infty)$/.test(destinoTextual)) {
    return [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
  }
  if (/^(?:-oo|-∞|menos infinito|-\\infty)$/.test(destinoTextual)) {
    return [-1000, -500, -200, -100, -50, -20, -10, -5, -2, -1];
  }
  if (base.length !== 10 || destinoNumerico(destino) !== null || !evaluadores.length) return base;
  const izquierda = Number(desde), derecha = Number(hasta), ancho = derecha - izquierda;
  const paso = ancho / 240;
  const focos = [];
  for (const evaluar of evaluadores) {
    if (typeof evaluar !== 'function') continue;
    const muestras = Array.from({ length: 241 }, (_, i) => {
      const x = izquierda + i * paso;
      try { return { x, y: evaluar(x) }; } catch { return { x, y: NaN }; }
    });
    for (let i = 1; i < muestras.length - 1; i++) {
      const [anterior, actual, siguiente] = muestras.slice(i - 1, i + 2);
      const finitos = [anterior.y, actual.y, siguiente.y].every(Number.isFinite);
      const singular = !Number.isFinite(actual.y) && Number.isFinite(anterior.y) && Number.isFinite(siguiente.y);
      const raiz = finitos && (Math.abs(actual.y) < 1e-8 || anterior.y * siguiente.y < 0);
      const extremo = finitos && (actual.y - anterior.y) * (siguiente.y - actual.y) <= 0;
      if (singular || raiz || extremo) focos.push(actual.x);
    }
  }
  const unicos = [...new Set(focos.map((x) => Number(x.toFixed(4))))]
    .sort((a, b) => Math.abs(a - (izquierda + derecha) / 2) - Math.abs(b - (izquierda + derecha) / 2));
  if (!unicos.length) return base;
  const elegidos = [];
  for (const foco of unicos) {
    if (elegidos.every((valor) => Math.abs(valor - foco) > ancho / 30)) elegidos.push(foco);
    if (elegidos.length === 2) break;
  }
  const puntos = new Set([izquierda, derecha]);
  for (const foco of elegidos) {
    const cerca = Math.min(ancho / 80, .1);
    const desplazamientos = elegidos.length > 1 ? [-cerca, 0, cerca] : [-5 * cerca, -cerca, 0, cerca, 5 * cerca];
    for (const desplazamiento of desplazamientos) {
      const x = Number((foco + desplazamiento).toFixed(6));
      if (x >= izquierda && x <= derecha) puntos.add(x);
    }
  }
  for (const x of base) { if (puntos.size >= 10) break; puntos.add(Number(x.toFixed(6))); }
  return [...puntos].sort((a, b) => a - b).slice(0, 10);
}

/** Un punto editado no queda restringido por el intervalo que propuso la tabla. */
export function aplicarAbscisasManuales(propuestas, manuales = {}) {
  return propuestas.map((valor, indice) => {
    const manual = manuales[indice];
    return Number.isFinite(manual) ? manual : valor;
  });
}

export function tabularCurvas(abscisas, evaluadores) {
  return abscisas.map((x) => ({
    x,
    valores: evaluadores.map((evaluar) => {
      if (!evaluar) return null;
      const y = evaluar(x);
      return Number.isFinite(y) ? y : null;
    })
  }));
}
