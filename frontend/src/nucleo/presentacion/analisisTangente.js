/**
 * Construye la evidencia numérica necesaria para una recta tangente.
 *
 * Una pendiente provista por el servidor se contrasta con las dos pendientes
 * laterales. El respaldo numérico sólo se acepta si converge al reducir el paso
 * y, en un punto interior, las pendientes laterales son compatibles. De este
 * modo una cúspide o una derivada infinita no se convierten por accidente en
 * una recta horizontal.
 */

const TOLERANCIA_RELATIVA = 2e-3;
const TOLERANCIA_ABSOLUTA = 2e-4;

function cercanos(a, b) {
  const escala = Math.max(1, Math.abs(a), Math.abs(b));
  return Math.abs(a - b) <= TOLERANCIA_ABSOLUTA + TOLERANCIA_RELATIVA * escala;
}

function evaluar(evaluador, x) {
  try {
    const valor = evaluador?.(x);
    return Number.isFinite(valor) ? valor : null;
  } catch {
    return null;
  }
}

function pendientesLaterales(funcion, x, y, h) {
  const menos = evaluar(funcion, x - h);
  const mas = evaluar(funcion, x + h);
  return {
    izquierda: menos === null ? null : (y - menos) / h,
    derecha: mas === null ? null : (mas - y) / h,
  };
}

function estimarInterior(funcion, x, y, h) {
  const grande = pendientesLaterales(funcion, x, y, h);
  const pequeno = pendientesLaterales(funcion, x, y, h / 2);
  const cuatro = [grande.izquierda, grande.derecha, pequeno.izquierda, pequeno.derecha];
  if (cuatro.some((valor) => valor === null || !Number.isFinite(valor))) return null;
  if (!cercanos(grande.izquierda, grande.derecha)) return null;
  if (!cercanos(pequeno.izquierda, pequeno.derecha)) return null;
  const estimacionGrande = (grande.izquierda + grande.derecha) / 2;
  const estimacionPequena = (pequeno.izquierda + pequeno.derecha) / 2;
  return cercanos(estimacionGrande, estimacionPequena) ? estimacionPequena : null;
}

function estimarUnLado(funcion, x, y, h, direccion) {
  const estimar = (paso) => {
    const uno = evaluar(funcion, x + direccion * paso);
    const dos = evaluar(funcion, x + direccion * 2 * paso);
    if (uno === null || dos === null) return null;
    return direccion > 0
      ? (-3 * y + 4 * uno - dos) / (2 * paso)
      : (3 * y - 4 * uno + dos) / (2 * paso);
  };
  const grande = estimar(h);
  const pequena = estimar(h / 2);
  if (grande === null || pequena === null || !Number.isFinite(grande) || !Number.isFinite(pequena)) {
    return null;
  }
  return cercanos(grande, pequena) ? pequena : null;
}

export function calcularTangente(funcion, derivada, x) {
  const punto = Number(x);
  const y = evaluar(funcion, punto);
  if (y === null) {
    return { disponible: false, motivo: 'La función no tiene un valor finito en ese punto.' };
  }

  const simbolica = evaluar(derivada, punto);
  const h = Math.max(1, Math.abs(punto)) * 1e-3;
  const laterales = pendientesLaterales(funcion, punto, y, h);
  let pendiente = null;
  let lado = null;

  if (laterales.izquierda !== null && laterales.derecha !== null) {
    pendiente = estimarInterior(funcion, punto, y, h);
    if (pendiente === null) {
      return {
        disponible: false,
        x: punto,
        y,
        motivo: 'Las pendientes laterales no convergen a una misma pendiente finita.'
      };
    }
  } else if (laterales.derecha !== null) {
    pendiente = estimarUnLado(funcion, punto, y, h, 1);
    lado = 'derecha';
  } else if (laterales.izquierda !== null) {
    pendiente = estimarUnLado(funcion, punto, y, h, -1);
    lado = 'izquierda';
  }

  if (simbolica !== null && pendiente !== null && lado === null && cercanos(simbolica, pendiente)) {
    return { disponible: true, x: punto, y, pendiente: simbolica, origen: 'simbolica' };
  }

  if (pendiente === null || !Number.isFinite(pendiente)) {
    return {
      disponible: false,
      x: punto,
      y,
      motivo: 'No hay evidencia numérica estable de una pendiente finita en ese punto.'
    };
  }

  return { disponible: true, x: punto, y, pendiente, origen: 'numerica', lado };
}

export function describirTangente(resultado) {
  if (!resultado?.disponible) return `Tangente no disponible. ${resultado?.motivo ?? ''}`.trim();
  const { x, y, pendiente, origen, lado } = resultado;
  const detalle = origen === 'simbolica'
    ? 'La pendiente procede de la derivada simbólica recibida.'
    : `La pendiente es una aproximación numérica${lado ? ` por la ${lado}` : ''}; no es una derivada simbólica exacta.`;
  return `Tangente en x=${x}: y=f(${x})+f′(${x})(x−${x}) = ${y}+${pendiente}(x−${x}). ${detalle}`;
}
