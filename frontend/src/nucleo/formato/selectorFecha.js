export function descomponerFecha(valor, conHora = false) {
  const coincide = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(String(valor ?? ''));
  const hoy = new Date();
  return {
    ano: coincide?.[1] ?? String(hoy.getFullYear()),
    mes: coincide?.[2] ?? '01',
    dia: coincide?.[3] ?? '01',
    hora: conHora ? coincide?.[4] ?? '00' : '00',
    minuto: conHora ? coincide?.[5] ?? '00' : '00',
    segundo: conHora ? coincide?.[6] ?? '00' : '00'
  };
}

export function diasDelMes(ano, mes) {
  return new Date(Number(ano), Number(mes), 0).getDate();
}

export function cambiarParteFecha(valor, parte, nuevo, conHora = false) {
  const piezas = { ...descomponerFecha(valor, conHora), [parte]: String(nuevo).padStart(2, '0') };
  piezas.dia = String(Math.min(Number(piezas.dia), diasDelMes(piezas.ano, piezas.mes))).padStart(2, '0');
  const fecha = `${piezas.ano}-${piezas.mes}-${piezas.dia}`;
  return conHora ? `${fecha}T${piezas.hora}:${piezas.minuto}:${piezas.segundo}` : fecha;
}

export function fechaBogota(desplazamiento = 0, instante = new Date()) {
  const fecha = new Date(instante.getTime() + desplazamiento * 86400000);
  const partes = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(fecha);
  const obtener = (tipo) => partes.find((parte) => parte.type === tipo)?.value;
  return `${obtener('year')}-${obtener('month')}-${obtener('day')}`;
}

export function diasDelCalendario(mes) {
  if (!/^\d{4}-\d{2}$/.test(mes)) return [];
  const [ano, numeroMes] = mes.split('-').map(Number);
  const primero = new Date(Date.UTC(ano, numeroMes - 1, 1));
  const desplazamiento = (primero.getUTCDay() + 6) % 7;
  const cantidad = diasDelMes(ano, numeroMes);
  const celdas = Math.ceil((desplazamiento + cantidad) / 7) * 7;
  return Array.from({ length: celdas }, (_, indice) => {
    const fecha = new Date(Date.UTC(ano, numeroMes - 1, indice - desplazamiento + 1));
    const valor = `${fecha.getUTCFullYear()}-${String(fecha.getUTCMonth() + 1).padStart(2, '0')}-${String(fecha.getUTCDate()).padStart(2, '0')}`;
    return { valor, dia: fecha.getUTCDate(), actual: fecha.getUTCMonth() + 1 === numeroMes };
  });
}

export function moverMes(mes, desplazamiento) {
  const [ano, numeroMes] = mes.split('-').map(Number);
  const fecha = new Date(Date.UTC(ano, numeroMes - 1 + desplazamiento, 1));
  return `${fecha.getUTCFullYear()}-${String(fecha.getUTCMonth() + 1).padStart(2, '0')}`;
}
