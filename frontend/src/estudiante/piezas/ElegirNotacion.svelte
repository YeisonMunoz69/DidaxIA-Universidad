
<script>
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { NOTACIONES, ADMITIDAS, POR_DEFECTO } from '../../nucleo/formato/notaciones.js';

  const elegida = $derived(preferencias.notacion || POR_DEFECTO);
</script>

<fieldset class="notacion">
  <legend>Notación de las derivadas</legend>
  <div class="rejilla-notaciones">
    {#each ADMITIDAS as id (id)}
      <label class="tarjeta-notacion" class:activa={elegida === id}>
        <input
          type="radio"
          name="notacion"
          value={id}
          checked={elegida === id}
          onchange={() => preferencias.elegirNotacion(id)} />
        <span class="circulo-radio" aria-hidden="true">
          <span class="punto-radio"></span>
        </span>
        <span class="info-notacion">
          <span class="nombre">{NOTACIONES[id].nombre}</span>
          <span class="ejemplo">{NOTACIONES[id].ejemplo}</span>
        </span>
      </label>
    {/each}
  </div>
</fieldset>

<style>
  .notacion {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
    margin: 0;
    padding: 0;
    border: 0;
    inline-size: 100%;
  }

  legend {
    padding: 0;
    font-size: var(--texto-sm);
    font-weight: 500;
    color: var(--ink-secondary);
  }

  .rejilla-notaciones {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--espacio-sm);
  }

  .tarjeta-notacion {
    position: relative;
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition);
  }

  .tarjeta-notacion:hover {
    border-color: var(--trazo);
  }

  .tarjeta-notacion.activa {
    border-color: var(--accent-main);
  }

  .tarjeta-notacion input[type="radio"] {
    position: absolute;
    opacity: 0;
    inline-size: 0;
    block-size: 0;
    pointer-events: none;
  }

  .circulo-radio {
    inline-size: 18px;
    block-size: 18px;
    border-radius: 50%;
    border: 1.5px solid var(--trazo);
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: var(--transition);
  }

  .tarjeta-notacion:hover .circulo-radio {
    border-color: var(--ink-secondary);
  }

  .tarjeta-notacion.activa .circulo-radio {
    border-color: var(--accent-main);
  }

  .punto-radio {
    inline-size: 8px;
    block-size: 8px;
    border-radius: 50%;
    background: var(--accent-main);
    transform: scale(0);
    transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .tarjeta-notacion.activa .punto-radio {
    transform: scale(1);
  }

  .info-notacion {
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow: hidden;
  }

  .nombre {
    font-size: var(--texto-xs);
    font-weight: 500;
    color: var(--ink-primary);
  }

  .ejemplo {
    font-family: var(--fuente-mono);
    font-size: var(--texto-xs);
    color: var(--accent-main);
  }
</style>
