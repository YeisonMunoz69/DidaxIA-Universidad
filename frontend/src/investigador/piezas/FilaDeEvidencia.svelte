
<script>
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import Icono from '../../comun/base/Icono.svelte';
  import { fechaLegible } from '../../nucleo/formato/fechas.js';

  let {
    evidencia,
    seleccionada = false,
    hermanos = 1,
    alSeleccionar
  } = $props();

  const ESTADOS = {
    pendiente: 'Sin revisar',
    aprobada: 'Aprobada',
    rechazada: 'Rechazada'
  };

  const referencia = $derived(String(evidencia?.sujeto ?? '').slice(-8));

  const nombreDelEstudiante = $derived(
    String(evidencia?.estudiante?.nombre ?? '').trim() || 'Nombre no disponible'
  );
  const clasesDelEstudiante = $derived(
    Array.isArray(evidencia?.estudiante?.clases)
      ? evidencia.estudiante.clases.filter(Boolean)
      : []
  );

  const kilobytes = $derived(Math.max(1, Math.round((evidencia?.tamano_bytes ?? 0) / 1024)));
</script>

<button
  type="button"
  class="fila"
  class:seleccionada
  aria-current={seleccionada ? 'true' : undefined}
  onclick={() => alSeleccionar?.(evidencia.evidencia)}
>
  <span class="cabeza">
    <span class="intento">Intento {evidencia.intento}</span>
    <span class="estado {evidencia.estado}">{ESTADOS[evidencia.estado] ?? evidencia.estado}</span>
  </span>

  <span class="linea">
    Recibida el {fechaLegible(evidencia.recibido_en)} · {kilobytes} KB
  </span>

  <span class="identidad-estudiante">{nombreDelEstudiante}</span>
  <span class="linea clase">
    {clasesDelEstudiante.length
      ? `${clasesDelEstudiante.length === 1 ? 'Clase' : 'Clases'}: ${clasesDelEstudiante.join(' · ')}`
      : 'Sin clase vinculada'}
  </span>

  <span class="linea tenue">
    <span class="rotulo">Estudiante (referencia técnica)</span>
    <code use:ayudaContextual title={evidencia.sujeto}>…{referencia}</code>
  </span>

  {#if hermanos > 1}
    <span class="hermanos">
      <Icono nombre="historial" medida={13} />
      <span>{hermanos} intentos de este estudiante en la lista</span>
    </span>
  {/if}
</button>

<style>
  .fila {
    display: flex;
    flex-direction: column;
    gap: 4px;
    inline-size: 100%;
    padding: var(--espacio-sm) var(--espacio-md);
    text-align: start;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .fila:hover { border-color: var(--accent-main); }

  .fila.seleccionada {
    border-color: var(--accent-main);
    background: var(--accent-surface);
  }

  .cabeza {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
  }

  .intento {
    font-size: var(--texto-base);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .estado {
    padding: 2px 9px;
    border-radius: var(--radius-pill, 9999px);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--trazo-suave);
    color: var(--ink-secondary);
    background: var(--surface-paper);
    white-space: nowrap;
  }

  .estado.aprobada {
    color: var(--semantic-success);
    background: var(--semantic-success-bg);
    border-color: var(--semantic-success);
  }

  .estado.rechazada {
    color: var(--semantic-danger, var(--ink-secondary));
    background: var(--semantic-danger-bg, var(--surface-paper));
    border-color: var(--semantic-danger, var(--trazo-suave));
  }

  .linea {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .identidad-estudiante {
    color: var(--ink-primary);
    font-size: var(--texto-sm);
    font-weight: 700;
  }

  .clase { color: var(--accent-main); font-weight: 650; }

  .linea.tenue {
    display: flex;
    align-items: baseline;
    gap: 6px;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .rotulo { text-transform: none; }

  code {
    font-family: var(--fuente-mono, monospace);
    font-size: var(--texto-xs);
  }

  .hermanos {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }
</style>
