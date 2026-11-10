let avisos = $state([]);
let siguienteId = 0;

function mostrar(tipo, mensaje) {
  const id = ++siguienteId;
  avisos = [...avisos, { id, tipo, mensaje: String(mensaje) }];
  setTimeout(() => { avisos = avisos.filter((aviso) => aviso.id !== id); }, 3500);
  return id;
}

export const toast = {
  get avisos() { return avisos; },
  descarga: (mensaje) => mostrar('descarga', mensaje),
  exito: (mensaje) => mostrar('confirmar', mensaje),
  alerta: (mensaje) => mostrar('cerrar-sesion', mensaje),
  error: (mensaje) => mostrar('eliminar', mensaje),
  comunicar: (mensaje) => mostrar('comunicar', mensaje),
};
