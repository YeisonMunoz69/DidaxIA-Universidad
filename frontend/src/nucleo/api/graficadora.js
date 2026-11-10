import { pedir, RUTAS } from './cliente.js';

export async function prepararCurvas(curvas) {
  return pedir(RUTAS.graficadora, { metodo: 'POST', cuerpo: { curvas } });
}
