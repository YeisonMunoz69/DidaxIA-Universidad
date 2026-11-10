import { pedir, RUTAS } from './cliente.js';

export function consultar() {
  return pedir(RUTAS.preferenciasNotificacion);
}

export function guardar(categoria, habilitada) {
  return pedir(
    `${RUTAS.preferenciasNotificacion}/${encodeURIComponent(categoria)}`,
    { metodo: 'PATCH', cuerpo: { habilitada } }
  );
}
