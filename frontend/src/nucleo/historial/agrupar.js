/**
 * Agrupar la lista de conversaciones por fecha, para el carril.
 *
 * Funciones puras, sacadas de `Aplicacion.svelte` el 2026-08-22 al partir el
 * armazón en piezas —ver `comun/armazon/CarrilHistorial.svelte`, su único
 * consumidor—. Sin estado y sin Svelte de por medio: se pueden probar solas.
 *
 */

/** «Hoy», «Ayer», o la hora/fecha —según qué tan lejos esté—, para una fila
    del carril. Cadena vacía si no hay marca o no se puede leer. */
export function formatearMomentoItem(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    const ahora = new Date();
    const esHoy = d.toDateString() === ahora.toDateString();
    if (esHoy) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    const ayer = new Date(ahora);
    ayer.setDate(ahora.getDate() - 1);
    if (d.toDateString() === ayer.toDateString()) {
      return 'Ayer';
    }
    return d.toLocaleDateString([], { day: 'numeric', month: 'short' });
  } catch {
    return '';
  }
}

/** La lista de conversaciones, partida en «Hoy» · «Ayer» · «Últimos 7 días»
    · «Anteriores». Solo entran los grupos que tienen algo. */
export function agruparPorFecha(lista) {
  if (!Array.isArray(lista) || lista.length === 0) return [];
  const grupos = [
    { id: 'hoy', titulo: 'Hoy', elementos: [] },
    { id: 'ayer', titulo: 'Ayer', elementos: [] },
    { id: 'semana', titulo: 'Últimos 7 días', elementos: [] },
    { id: 'anteriores', titulo: 'Anteriores', elementos: [] }
  ];

  const ahora = new Date();
  const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate()).getTime();
  const inicioAyer = inicioHoy - 86400000;
  const inicioSemana = inicioHoy - 7 * 86400000;

  for (const item of lista) {
    const fecha = item.ultimo || item.inicio;
    const t = fecha ? new Date(fecha).getTime() : 0;

    if (!t || t >= inicioHoy) {
      grupos[0].elementos.push(item);
    } else if (t >= inicioAyer) {
      grupos[1].elementos.push(item);
    } else if (t >= inicioSemana) {
      grupos[2].elementos.push(item);
    } else {
      grupos[3].elementos.push(item);
    }
  }

  return grupos.filter((g) => g.elementos.length > 0);
}
