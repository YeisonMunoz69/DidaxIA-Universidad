export const CLAVE_TEMA = 'agente-calculo.tema';
export const TEMAS = ['sistema', 'claro', 'oscuro'];

export function leerTema() {
  try {
    const valor = globalThis.localStorage?.getItem(CLAVE_TEMA);
    return TEMAS.includes(valor) ? valor : 'sistema';
  } catch {
    return 'sistema';
  }
}

export function guardarTema(valor) {
  if (!TEMAS.includes(valor)) return false;
  try { globalThis.localStorage?.setItem(CLAVE_TEMA, valor); } catch {  }
  return true;
}
