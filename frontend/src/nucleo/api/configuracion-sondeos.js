/** Gobierno curricular: la autoridad del estado es el servidor. */
import { pedir, RUTAS } from './cliente.js';

export function consultar() {
  return pedir(RUTAS.configuracionSondeos);
}

export function cambiarNodo(nodo, habilitado) {
  return pedir(
    `${RUTAS.configuracionSondeos}/nodos/${encodeURIComponent(nodo)}`,
    { metodo: 'PATCH', cuerpo: { habilitado } }
  );
}

export function cambiarUmbral(umbral_intentos) {
  return pedir(`${RUTAS.configuracionSondeos}/umbral`,
    { metodo: 'PATCH', cuerpo: { umbral_intentos } });
}
