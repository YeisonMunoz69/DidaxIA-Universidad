/**
 * Proyecciones del material visible de una conversación.
 *
 * El hilo sigue siendo la única fuente. Estas funciones no acumulan estado ni
 * inventan relaciones de evidencia: seleccionan gráficas, notación y conceptos
 * que los turnos ya contienen, conservando su orden.
 */
import { esNombreHumano } from './identificadores.js';

/** @param {{tipo?: string, contenido?: string, alternativo?: string}[]} bloques */
function bloquesDeGaleria(bloques, indiceDeTurno, contexto = {}) {
  return bloques
    .filter((bloque) => bloque?.tipo === 'grafica' || bloque?.tipo === 'notacion')
    .map((bloque, indice) => ({
      ...bloque,
      clave: `${indiceDeTurno}-${indice}`,
      indiceDeTurno,
      ...contexto,
    }));
}

/** @param {{turno?: {bloques?: object[]}}[]} hilo */
export function itemsDeGaleria(hilo = []) {
  return (hilo ?? []).flatMap((entrada, indice) => {
    const turno = entrada?.turno;
    return bloquesDeGaleria(turno?.bloques ?? [], indice, {
      turno: turno?.turno,
      clase: turno?.clase,
      concepto: turno?.conceptos?.[0]?.id ?? turno?.citas?.[0]?.id,
    });
  });
}

/** @param {{indiceDeTurno: number}[]} items */
export function agruparItemsDeGaleria(items = []) {
  const porTurno = new Map();
  for (const item of items) {
    if (!porTurno.has(item.indiceDeTurno)) porTurno.set(item.indiceDeTurno, []);
    porTurno.get(item.indiceDeTurno).push(item);
  }
  return [...porTurno.entries()].map(([indiceDeTurno, itemsDelTurno]) => ({
    indiceDeTurno,
    items: itemsDelTurno
  }));
}

/** @param {{tipo?: string}[]} items */
export function comprimirGraficas(items = []) {
  return items.filter((item) => item?.tipo === 'grafica').length > 1;
}

/** @param {string | undefined} contenido */
export function traeDerivada(contenido) {
  try {
    return Boolean(JSON.parse(contenido ?? '')?.derivada_js);
  } catch {
    return false;
  }
}

/** Expresiones que acompañan a cada curva, sin inferir fórmulas del código JS. */
export function formulasDeGrafica(contenido) {
  try {
    const datos = JSON.parse(contenido ?? '');
    const curvas = Array.isArray(datos?.curvas) && datos.curvas.length
      ? datos.curvas : [datos];
    return curvas
      .map((curva, indice) => {
        let expresion = typeof curva?.expresion === 'string' ? curva.expresion.trim() : '';
        if (expresion.startsWith('$$') && expresion.endsWith('$$')) expresion = expresion.slice(2, -2).trim();
        else if (expresion.startsWith('$') && expresion.endsWith('$')) expresion = expresion.slice(1, -1).trim();
        else if (expresion.startsWith('\\(') && expresion.endsWith('\\)')) expresion = expresion.slice(2, -2).trim();
        if (!expresion) return null;
        const variable = /^[a-zA-Zθ]$/.test(curva.variable ?? '') ? curva.variable : 'x';
        const nombre = /^[a-zA-Z]$/.test(curva.nombre_funcion ?? '') ? curva.nombre_funcion : curvas.length > 1 ? `f_{${indice + 1}}` : 'f';
        return `${nombre}(${variable}) = ${expresion}`;
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * Conceptos humanos invocados por los turnos, sin confundir referencias
 * bibliográficas `F-*` con nombres pedagógicos.
 * @param {{turno?: {conceptos?: object[], citas?: object[]}}[]} hilo
 */
export function conceptosDelHilo(hilo = []) {
  const conceptos = new Map();
  for (const entrada of hilo ?? []) {
    const conceptosDelTurno = entrada?.turno?.conceptos;
    if (Array.isArray(conceptosDelTurno)) {
      for (const concepto of conceptosDelTurno) {
        if (concepto && esNombreHumano(concepto.nombre)) {
          conceptos.set(concepto.id || concepto.nombre, concepto);
        }
      }
    }

    const citasDelTurno = entrada?.turno?.citas;
    if (Array.isArray(citasDelTurno)) {
      for (const cita of citasDelTurno) {
        if (cita && esNombreHumano(cita.nombre)) {
          conceptos.set(cita.id || cita.nombre, {
            id: cita.id,
            nombre: cita.nombre,
            nodo: cita.nodo
          });
        }
      }
    }
  }
  return [...conceptos.values()];
}
