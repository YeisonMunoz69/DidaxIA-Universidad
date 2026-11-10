/** Evaluación finita del servidor que conserva las restricciones originales. */
export function compilarCurva(curva) {
  if (!curva?.funcion_js) return null;
  try {
    const evaluar = new Function('x', `return (${curva.funcion_js});`);
    const original = curva.dominio_js ? new Function('x', `return (${curva.dominio_js});`) : null;
    const excluidos = (curva.dominio?.puntos ?? []).filter(p =>
      ['no_definida', 'no_derivable'].includes(p.estado) || (curva.tipo === 'derivada' && p.estado === 'no_verificable')).map(p => p.x);
    return x => {
      try {
        if (excluidos.some(a => x === a) || (original && !Number.isFinite(original(x)))) return NaN;
        const y = evaluar(x);
        return typeof y === 'number' && Number.isFinite(y) ? y : NaN;
      } catch { return NaN; }
    };
  } catch { return null; }
}

export function describirPunto(punto, tipo, variable = 'x', nombreFuncion = 'f') {
  const valor = Number.isFinite(punto.valor) ? punto.valor : punto.estado === 'no_verificable' ? 'no se pudo verificar' : 'no está definida';
  const letra = /^[a-zA-Z]$/.test(nombreFuncion) ? nombreFuncion : 'f';
  const nombre = tipo === 'derivada' ? `${letra}′` : letra;
  let texto = `${nombre}(${punto.x}): ${valor}.`;
  if (Number.isFinite(punto.limite)) texto += ` Límite al acercarse a ${variable}=${punto.x}: ${punto.limite}.`;
  else if (punto.tipo === 'salto') texto += ` Los límites laterales son distintos: ${punto.izquierda} y ${punto.derecha}.`;
  else if (punto.tipo === 'asintota') texto += ' Hay un límite lateral infinito; no se marca un hueco finito.';
  else if (punto.tipo === 'no_verificable') texto += ' No se pudo verificar el comportamiento lateral.';
  else if (punto.tipo === 'frontera_o_no_convergente') texto += ' No se comprobó un único límite real finito por ambos lados.';
  return texto;
}
