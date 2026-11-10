export function describirPeriodo(periodo) {
  if (!periodo?.desde || !periodo?.hasta) return 'Periodo no disponible';
  const zona = periodo.zona_horaria || 'America/Bogota';
  const formato = new Intl.DateTimeFormat('es-CO', {
    timeZone: zona, day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  });
  return `Desde ${formato.format(new Date(periodo.desde))} hasta ${formato.format(new Date(periodo.hasta))} (${zona}). El inicio se incluye y el final se excluye.`;
}
