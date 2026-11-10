
<script>
  import Icono from '../base/Icono.svelte';
  import TituloDeConversacion from './TituloDeConversacion.svelte';
  import { formatearMomentoItem } from '../../nucleo/historial/agrupar.js';

  let { grupo, sesionSeleccionada = null, alAbrir } = $props();
</script>

<div class="grupo-fecha">
  <p class="epigrafe-fecha">{grupo.titulo}</p>
  <ul class="lista-recientes">
    {#each grupo.elementos as conversacion (conversacion.sesion)}
      <li>
        <button
          type="button"
          class="sesion-pasada"
          aria-current={sesionSeleccionada === conversacion.sesion ? 'page' : undefined}
          onclick={() => alAbrir(conversacion.sesion)}>
          <Icono nombre="conversacion" medida={15} />
          <span class="texto">
            <span class="rotulo"><TituloDeConversacion titulo={conversacion.titulo} /></span>
            <span class="sub">
              {#if conversacion.ultimo || conversacion.inicio}
                <span class="momento">
                  {formatearMomentoItem(conversacion.ultimo || conversacion.inicio)}
                </span>
                <span class="separador" aria-hidden="true">·</span>
              {/if}
              <span class="turnos-conteo">{conversacion.turnos}t</span>
            </span>
          </span>
        </button>
      </li>
    {/each}
  </ul>
</div>

<style>
  ul {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-block-size: 34px;
    inline-size: 100%;
    box-sizing: border-box;
    padding: 5px 8px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--ink-secondary);
    font: inherit;
    font-size: 12px;
    text-align: start;
    cursor: pointer;
    transition: all 0.2s ease-out;
  }

  button :global(svg) { flex-shrink: 0; transition: transform 0.2s ease-out; }
  button:hover {
    background: var(--surface-panel);
    border-color: var(--trazo-suave);
    color: var(--ink-primary);
  }
  button:hover :global(svg) { transform: scale(1.15); }
  button[aria-current='page'] {
    background: var(--accent-surface);
    border-color: var(--accent-main);
    color: var(--accent-main);
    font-weight: 600;
  }

  .grupo-fecha { margin-block-end: 12px; }
  .grupo-fecha:last-child { margin-block-end: 0; }

  .epigrafe-fecha {
    margin: 6px 0 4px 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-tertiary);
    opacity: 0.85;
  }

  .sesion-pasada { position: relative; overflow: hidden; }
  .texto {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-inline-size: 0;
    flex: 1;
  }

  .rotulo {
    min-inline-size: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
    font-weight: 500;
    color: inherit;
  }

  .sub {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 1px 5px;
    background: var(--surface-panel);
    border-radius: var(--radius-xs);
    color: var(--ink-tertiary);
    font-size: 9.5px;
    font-weight: 600;
    opacity: 0.85;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .momento { font-weight: 500; }
  .separador { opacity: 0.6; margin: 0 1px; }
  .turnos-conteo { font-weight: 700; }
  .sesion-pasada[aria-current='page'] .sub {
    background: var(--accent-surface);
    color: var(--accent-main);
    opacity: 1;
  }

  @media (prefers-reduced-motion: reduce) {
    .sesion-pasada:hover { transform: none; }
  }
</style>
