<!--
El estado degradado, con la última fase alcanzada cuando la hay.

`RP-17` obliga a degradarse de forma SEGURA Y EXPLICITA ante el fallo del motor
simbólico o del generador. Las dos palabras importan: segura significa que no
llega contenido matemático sin sello, y explícita significa que el estudiante se
entera de que algo falló en vez de quedarse esperando.

LA ULTIMA FASE ES LA NOVEDAD. Antes de `DD-11` la degradación solo podía decir
«algo falló». Ahora puede decir en qué punto del turno se quedó, porque las
fases ya alcanzadas viajaron antes del fallo. Es la primera utilidad práctica de
emitir el turno por partes.

TRES SITUACIONES DISTINTAS, y confundirlas incumple un requisito distinto en
cada caso — ver contrato §8:

  degradado        · algo falló. Se puede reintentar.
  fuera-de-dominio · la consulta no es de cálculo diferencial. RP-18 pide
                     rechazo EXPLICATIVO, no un «no puedo ayudarte».
  fuera-de-alcance · señales que exceden lo pedagógico. NO se ofrece
                     reintentar: reintentar sería insistir con la interacción
                     que se acaba de interrumpir a propósito.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import AnimacionBallenaDeepSeek from './AnimacionBallenaDeepSeek.svelte';
  import { modoDeContingencia } from '../../nucleo/errores/degradacion.js';
  let {
    /** { situacion, explicacion?, mensaje?, ultima_fase? } — contrato §8 */
    respuesta,
    /** Se invoca solo cuando reintentar tiene sentido. */
    alReintentar = null,
    /** El chat reserva una franja más alta dentro de su hilo desplazable. */
    amplio = false
  } = $props();

  const situacion = $derived(respuesta?.situacion);
  const modo = $derived(modoDeContingencia(respuesta));

  // Reintentar NO se ofrece ante fuera-de-alcance. Es la regla que no se toca.
  const sePuedeReintentar = $derived(
    situacion === 'degradado' && respuesta?.reintentable !== false && typeof alReintentar === 'function'
  );

  const TITULO = {
    degradado:          'No se pudo completar la respuesta',
    'fuera-de-dominio': 'Esto queda fuera de lo que puedo acompañar',
    'fuera-de-alcance': 'Prefiero que hables con alguien'
  };
</script>

<section class="degradacion {situacion}" class:contingencia={Boolean(modo)} role="alert" aria-live="polite">
  {#if modo}<AnimacionBallenaDeepSeek {modo} {amplio} />{/if}
  <h3>{modo === 'offline' ? 'No hay conexión' : modo === 'error_respuesta' && respuesta?.clase !== 'mantenimiento'
    ? 'No se pudo completar la respuesta.' : respuesta?.titulo || TITULO[situacion] || 'No se pudo completar la respuesta'}</h3>

  <p>{modo === 'offline' ? 'No consigo llegar al servidor del curso. Puede ser la red de aquí.' : respuesta?.explicacion || respuesta?.mensaje ||
      'Ocurrió un problema al preparar la respuesta.'}</p>

  {#if situacion === 'degradado' && respuesta?.ultima_fase}
    <p class="ultima">
      Se quedó en: <strong>{respuesta.ultima_fase}</strong>
    </p>
  {/if}

  {#if sePuedeReintentar}
    <button type="button" onclick={alReintentar}>Intentar de nuevo</button>
  {/if}
</section>

<style>
  .degradacion {
    padding: var(--espacio-md) var(--espacio-lg);
    border-radius: var(--radius-trazado);
    max-inline-size: var(--ancho-lectura);
  }

  .degradacion.contingencia {
    inline-size:100%; max-inline-size:none; min-inline-size:0; flex-shrink:0;
    margin-block:var(--espacio-md); padding:var(--espacio-md);
    background:var(--surface-paper); border:1px solid var(--trazo-suave);
    color:var(--ink-primary);
  }
  .contingencia h3 { margin-block-start:var(--espacio-md); }

  /* `border` completo, no `border-inline-start`: la franja de un solo
     lado era la excepción en el árbol, no la norma —
     `docente/rutas/FichaDeEstudiante.svelte::.aviso` y el resto de avisos
     del sistema usan un borde entero del color semántico—. Este
     componente es compartido por los dos árboles, así que el arreglo
     alcanza cualquier pantalla que lo use, no solo las de docente. */
  .degradado,
  .fuera-de-dominio {
    background: var(--semantic-warning-bg);
    border: 1px solid var(--semantic-warning);
  }

  /* Fuera de alcance no se pinta como error: no lo es. Es una decisión
     deliberada del sistema y el tono acompaña. */
  .fuera-de-alcance {
    background: var(--semantic-info-bg);
    border: 1px solid var(--semantic-info);
  }

  h3 {
    margin: 0 0 0.35rem;
    font-size: var(--texto-md);
  }

  p { margin: 0 0 0.4rem; font-size: var(--texto-sm); }

  .ultima { color: var(--ink-secondary); }

  /* Es el único control de una pieza que aparece cuando algo ya salió mal:
     que se vea dónde empieza no es un detalle. `--ink-ghost` está exento del
     mínimo de `1.4.11` y aquí el borde es lo único que lo delimita. */
  button {
    min-block-size: 44px;
    padding: 0.4em 0.9em;
    background: var(--surface-paper);
    color: var(--ink-primary);
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    font-size: var(--texto-sm);
    transition: var(--transition-fast);
  }

  button:hover { border-color: var(--accent-main); color: var(--accent-main); }

  button:active { transform: translateY(1px); }
</style>
