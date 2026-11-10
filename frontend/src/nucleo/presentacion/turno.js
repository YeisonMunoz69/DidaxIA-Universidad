/**
 * Proyección de los bloques de un turno a párrafos visibles.
 *
 * Conserva en un módulo puro las reglas de agrupación y de consistencia. La
 * vista decide cómo pintar cada grupo, pero no vuelve a interpretar el orden o
 * los sellos de los bloques.
 */

const TIPOS_EN_FRASE = new Set(['prosa', 'expresion-citada']);
const SOLO_SIGNOS = /^[\s\p{P}\p{S}]+$/u;

/**
 * @param {{tipo?: string, contenido?: string, sello?: string}[]} lista
 * @returns {{enFrase: boolean, sello?: string, bloques: object[], cierre: string}[]}
 */
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

/** @param {{tipo?: string}[]} bloques @param {number} indice */
export function esPrimeraCitaDeLaFrase(bloques, indice) {
  return bloques.findIndex((bloque) => bloque?.tipo === 'expresion-citada') === indice;
}

/**
 * Un sondeo no puede llevar un bloque verificado: es la condición C4 de
 * ADR-014, expresada sin depender del componente que la presenta.
 * @param {{nivel?: string, bloques?: {sello?: string}[]} | null | undefined} turno
 */
export function esTurnoMalformado(turno) {
  return turno?.nivel === 'sondeo'
    && (turno?.bloques ?? []).some((bloque) => bloque?.sello === 'verificado');
}

/**
 * Texto portable de una respuesta para el botón «Copiar».
 *
 * La gráfica no se serializa como su JSON interno: se copia su descripción
 * editorial. Las expresiones se conservan entre delimitadores `$` para que
 * puedan pegarse en otro editor matemático sin perder su intención.
 */
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
