
<script>
  import AnimacionBallenaDeepSeek from './AnimacionBallenaDeepSeek.svelte';
  import { modoDeContingencia } from '../../nucleo/errores/degradacion.js';
  let {
    respuesta,
    alReintentar = null,
    amplio = false
  } = $props();

  const situacion = $derived(respuesta?.situacion);
  const modo = $derived(modoDeContingencia(respuesta));

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

  .degradado,
  .fuera-de-dominio {
    background: var(--semantic-warning-bg);
    border: 1px solid var(--semantic-warning);
  }

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
