
const TIPOS_EN_FRASE = new Set(['prosa', 'expresion-citada']);
const SOLO_SIGNOS = /^[\s\p{P}\p{S}]+$/u;

export function agruparBloquesDelTurno(lista = []) {
  const grupos = [];
  for (const bloque of lista) {
    const ultimo = grupos[grupos.length - 1];
    const enFrase = TIPOS_EN_FRASE.has(bloque?.tipo);

    if (ultimo && bloque?.tipo === 'prosa' && SOLO_SIGNOS.test(bloque.contenido ?? '')) {
      ultimo.cierre += bloque.contenido;
      continue;
    }

    if (ultimo?.enFrase && enFrase && ultimo.sello === bloque?.sello) {
      ultimo.bloques.push(bloque);
    } else {
      grupos.push({ enFrase, sello: bloque?.sello, bloques: [bloque], cierre: '' });
    }
  }
  return grupos;
}

export function esPrimeraCitaDeLaFrase(bloques, indice) {
  return bloques.findIndex((bloque) => bloque?.tipo === 'expresion-citada') === indice;
}

export function esTurnoMalformado(turno) {
  return turno?.nivel === 'sondeo'
    && (turno?.bloques ?? []).some((bloque) => bloque?.sello === 'verificado');
}

export function textoCopiableDelTurno(turno) {
  const convertir = (bloque) => {
      if (bloque?.tipo === 'grafica') return bloque.alternativo ?? '';
      if (bloque?.tipo === 'notacion' || bloque?.tipo === 'expresion-citada') {
        return bloque.contenido ? `$${bloque.contenido}$` : '';
      }
      return bloque?.contenido ?? '';
  };

  return agruparBloquesDelTurno(turno?.bloques ?? [])
    .map((grupo) => `${grupo.bloques.map(convertir).join(grupo.enFrase ? '' : '\n')}${grupo.cierre}`)
    .filter(Boolean)
    .join('\n')
    .trim();
}
