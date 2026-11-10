
<script>
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  let {
    filtros = $bindable({ urgencia: '', clase: '', tipo: '' }),
    clases = []
  } = $props();

  const URGENCIAS = [['', 'Cualquier urgencia'], ['alta', 'Alta'],
                     ['normal', 'Normal'], ['baja', 'Baja']];
  const TIPOS = [['', 'Cualquier tipo'], ['respuesta', 'Respuesta al estudiante'],
                 ['sin-fuente', 'Sin material que la respalde'],
                 ['degradado', 'Turno degradado']];
</script>

<fieldset class="filtros">
  <legend>Acotar la cola</legend>

  <label>
    Urgencia
    <select use:menuDesplegable={filtros.urgencia} bind:value={filtros.urgencia}>
      {#each URGENCIAS as [v, t] (v)}<option value={v}>{t}</option>{/each}
    </select>
  </label>

  <label>
    Clase
    <select use:menuDesplegable={filtros.clase} bind:value={filtros.clase}>
      <option value="">Cualquier clase</option>
      {#each clases as c (c.id)}<option value={c.id}>{c.nombre}</option>{/each}
    </select>
  </label>

  <label>
    Tipo
    <select use:menuDesplegable={filtros.tipo} bind:value={filtros.tipo}>
      {#each TIPOS as [v, t] (v)}<option value={v}>{t}</option>{/each}
    </select>
  </label>
</fieldset>

<style>
  .filtros {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 1.1rem;
    margin: 0;
    padding: var(--espacio-md) var(--espacio-lg);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
  }

  legend {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    margin-inline-start: -2px;
    margin-block-start: -0.9em;
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--accent-main);
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3em;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    font-weight: 500;
  }

  select {
    padding: 0.5em 2.1em 0.5em 0.7em;
    background-color: var(--surface-paper);
    background-image:
      linear-gradient(45deg, transparent 50%, var(--ink-secondary) 50%),
      linear-gradient(135deg, var(--ink-secondary) 50%, transparent 50%);
    background-position:
      calc(100% - 1.1em) center,
      calc(100% - 0.75em) center;
    background-size: 0.35em 0.35em;
    background-repeat: no-repeat;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    color: var(--ink-primary);
    font-size: var(--texto-sm);
    font-family: inherit;
    appearance: none;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  select:hover { border-color: var(--ink-tertiary); }

  select:focus {
    border-color: var(--accent-main);
    outline: none;
    box-shadow: 0 0 0 2px var(--accent-glow);
  }
</style>
