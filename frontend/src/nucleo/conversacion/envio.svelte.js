/**
 * Orquestación de un turno de conversación.
 *
 * `enviar(mensaje, dosNiveles)` admite además la respuesta a un ítem de dos
 * niveles (`RC-PED-06`): viaja **junto** al mensaje del turno, no en lugar de
 * él, porque contestar el ítem no interrumpe la conversación.
 *
 * Decide a qué hilo se agrega, construye el contrato de la API, actualiza el
 * progreso, registra una degradación y recupera una sesión vencida. La ruta
 * conserva la presentación y entrega `alDesplazar`, porque solo ella conoce el
 * elemento que se mueve. Esta frontera permite probar y cambiar el envío sin
 * mezclarlo con el panel, el redactor ni el CSS de la pantalla.
 */
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

  /**
   * El turno completo que falló, para poder reintentar EL MISMO · paquete H.
   *
   * 🔴 Antes sólo se conservaba `ultimoMensaje`, así que el reintento perdía
   * `dosNiveles`: la respuesta al ítem se enviaba como un mensaje de texto
   * cualquiera y el diagnóstico no ocurría. Y como `enviar()` siempre agrega
   * el turno del estudiante al hilo, reintentar **duplicaba su mensaje** en
   * pantalla.
   *
   * Se guarda el payload entero y la clave de idempotencia: el servidor
   * reconoce el reintento por ella y no cuenta el turno dos veces
   * (`adaptadores/entrantes/http/concurrencia.py`).
   */
  let pendiente = $state(null);

  /**
   * Si el último turno **llegó al servidor**, aunque llegara degradado.
   *
   * No es lo mismo que «salió bien»: una respuesta degradada es una respuesta,
   * el turno se contó y contestarlo otra vez sería contarlo dos veces. Lo que
   * esto distingue es el caso en el que la petición **no llegó** —red caída,
   * error HTTP—, que es el único en el que reintentar tiene sentido y el único
   * en el que el ítem de dos niveles debe quedarse abierto con lo escrito
   * dentro (`SondeoDeDosNiveles.svelte`).
   */
  let entregado = $state(false);

  function nuevaClave() {
    // `randomUUID` existe en todo navegador con `crypto`; el respaldo cubre
    // los contextos donde no —y no tiene que ser criptográfico: sólo
    // irrepetible dentro de una conversación.
    return globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random()}`;
  }

  async function enviar(mensaje, dosNiveles = null, opciones = {}) {
    const { idempotencia = nuevaClave(), yaEnElHilo = false } = opciones;
    ultimoMensaje = mensaje;
    fallo = null;
    entregado = false;
    pendiente = { mensaje, dosNiveles, idempotencia };

    // Escribir sobre un hilo pasado lo retoma. `retomarSesion` viaja en cada
    // turno para que el backend lo archive bajo la charla que se está viendo.
    const retomando = historial.viendoHistorial;
    const sesionARetomar = retomando ? historial.sesionVista : null;
    const turnoEstudiante = { bloques: [{ tipo: 'prosa', contenido: mensaje }] };

    // `yaEnElHilo`: un reintento **no** vuelve a pintar el mensaje del
    // estudiante. Ya está arriba desde el primer intento, y agregarlo otra vez
    // le enseñaría dos veces lo que escribió una.
    if (yaEnElHilo) {
      // nada que agregar
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
          // §3.quater · la clave del paquete J. Viaja siempre para que un
          // reintento sea reconocible como tal.
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

      // Llegó y contestó, aunque la respuesta sea una degradación.
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

        // El backend ya registró el turno: la lista necesita reflejar una
        // conversación nueva o la nueva fecha/cantidad de una existente.
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

  /**
   * Reintenta **el mismo turno**: mismo mensaje, mismo `dosNiveles` y misma
   * clave de idempotencia, y sin volver a pintar lo que el estudiante escribió.
   */
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
