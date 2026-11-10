import { RUTAS, pedir } from './cliente.js';

export async function estado({ señal } = {}) {
  return pedir(RUTAS.onboardingEstado, { señal });
}

export async function guardarPerfil({ edad, facultad, programa, semestre, motivo = '' }, { señal } = {}) {
  const cuerpo = {};
  const facultadNormalizada = String(facultad ?? '').trim();
  const programaNormalizado = String(programa ?? '').trim();
  if (facultadNormalizada) cuerpo.facultad = facultadNormalizada;
  if (programaNormalizado) cuerpo.programa = programaNormalizado;
  if (edad !== null && edad !== undefined && edad !== '') cuerpo.edad = Number(edad);
  if (semestre !== null && semestre !== undefined && semestre !== '') {
    cuerpo.semestre = Number(semestre);
  }
  const motivoNormalizado = String(motivo ?? '').trim();
  if (motivoNormalizado) cuerpo.motivo = motivoNormalizado;
  return pedir(RUTAS.onboardingPerfil, { metodo: 'POST', cuerpo, señal });
}
