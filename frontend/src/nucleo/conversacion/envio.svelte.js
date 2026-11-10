import { enviarTurno } from '../api/turno.js';
import { crearProgreso } from '../fases/progreso.svelte.js';
import { clasificar, describir } from '../errores/degradacion.js';
import { preferencias } from '../preferencias/preferencias.svelte.js';
import { conversacion } from './conversacion.svelte.js';
import { sesion } from '../sesion/sesion.svelte.js';
import { historial } from '../historial/historial.svelte.js';

export function crearEnvioDeConversacion({ alDesplazar = () => {} } = {}) {
  const progreso = crearProgreso();
  let fallo = $state(null);
  let ocupado = $state(false);
  let ultimoMensaje = $state('');

  let pendiente = $state(null);

  let entregado = $state(false);

  function nuevaClave() {
    return globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random()}`;
  }

  async function enviar(mensaje, dosNiveles = null, opciones = {}) {
    const { idempotencia = nuevaClave(), yaEnElHilo = false } = opciones;
    ultimoMensaje = mensaje;
    fallo = null;
    entregado = false;
    pendiente = { mensaje, dosNiveles, idempotencia };

    const retomando = historial.viendoHistorial;
    const sesionARetomar = retomando ? historial.sesionVista : null;
    const turnoEstudiante = { bloques: [{ tipo: 'prosa', contenido: mensaje }] };

    if (yaEnElHilo) {
    } else if (retomando) {
      historial.agregarAlHiloVisto('estudiante', turnoEstudiante);
    } else {
      conversacion.agregarTurno('estudiante', turnoEstudiante);
    }

    ocupado = true;
    progreso.iniciar();
    alDesplazar(true);

    try {
      const respuesta = await enviarTurno(
        {
          sesion: sesion.conversacion,
          mensaje,
          notacion: preferencias.notacion,
          idempotencia,
          ...(sesionARetomar ? { retomarSesion: sesionARetomar } : {}),
          ...(dosNiveles ? { dosNiveles } : {})
        },
        {
          alFase: (fase) => {
            progreso.recibir({ fase: fase.id, texto: fase.texto });
            alDesplazar(false);
          }
        }
      );

      entregado = true;
      if (respuesta.degradado) {
        fallo = {
          ...respuesta.degradado,
          situacion: respuesta.degradado.situacion ?? 'degradado'
        };
        sesion.marcarDegradada(true);
      } else {
        if (retomando) {
          historial.agregarAlHiloVisto('tutor', respuesta.cuerpo);
          historial.marcarRetomado();
        } else {
          conversacion.agregarTurno('tutor', respuesta.cuerpo);
        }
        sesion.marcarDegradada(false);

        if (sesion.autenticada) historial.recargarLista();
      }
      alDesplazar(true);
    } catch (error) {
      if (clasificar(error) === 'sin-sesion') {
        await sesion.sincronizar();
        fallo = null;
      } else {
        fallo = describir(error, progreso.actual);
        sesion.marcarDegradada(true);
      }
      alDesplazar(true);
    } finally {
      progreso.terminar();
      ocupado = false;
      alDesplazar(true);
    }
  }

  async function reintentar() {
    if (!pendiente) return;
    const { mensaje, dosNiveles, idempotencia } = pendiente;
    await enviar(mensaje, dosNiveles, { idempotencia, yaEnElHilo: true });
  }

  return {
    progreso,
    get fallo() { return fallo; },
    get ocupado() { return ocupado; },
    get ultimoMensaje() { return ultimoMensaje; },
    get pendiente() { return pendiente; },
    get entregado() { return entregado; },
    enviar,
    reintentar
  };
}
