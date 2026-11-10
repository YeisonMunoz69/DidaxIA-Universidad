
<script>
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import Icono from '../../comun/base/Icono.svelte';

  let {
    titulo,
    ayuda = '',
    icono,
    insignia,
    accion,
    nota,
    notaGrande = false
  } = $props();
</script>

<header class="cabecera-de-ruta">
  <div class="fila-titulo">
    <div class="titulo-y-insignia">
      <h1>{titulo}</h1>
      <span class="insignia-modulo">
        <Icono nombre={icono} medida={13} />
        <span>{insignia}</span>
      </span>
      {#if ayuda}<BotonAyudaTooltip texto={ayuda} ariaLabel={`Ayuda sobre ${titulo}`} />{/if}
    </div>
    {#if accion}
      {@render accion()}
    {/if}
  </div>
  {#if nota}
    <p class="nota" class:grande={notaGrande}>{@render nota()}</p>
  {/if}
</header>

<style>
  .cabecera-de-ruta {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .fila-titulo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-lg);
  }

  .titulo-y-insignia {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .insignia-modulo {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--accent-main);
  }

  h1 {
    margin: 0;
    font-size: var(--texto-xl);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.2;
  }

  .nota {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
    line-height: 1.5;
  }

  .nota.grande {
    font-size: var(--texto-base);
    color: var(--ink-secondary);
  }
</style>
