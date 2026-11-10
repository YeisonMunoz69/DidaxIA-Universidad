
<script>
  let {
    estado
  } = $props();

  const ROTULO = {
    verificado: { signo: '✓', texto: 'Verificado simbólicamente' },
    generado:   { signo: '◇', texto: 'Explicación generada'      }
  };

  const sello = $derived(ROTULO[estado] ?? null);
</script>

{#if sello}
  <span class="sello {estado}">
    <span class="signo" aria-hidden="true">{sello.signo}</span>
    {sello.texto}
  </span>
{:else}

  <span class="sello desconocido">
    <span class="signo" aria-hidden="true">!</span>
    Estado de verificación no reconocido
  </span>
{/if}

<style>
  .sello {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.7em;
    border-radius: var(--radius-xl);
    font-size: var(--texto-xs);
    font-weight: 600;
    line-height: 1.4;
  }

  .signo { font-weight: 700; }

  .verificado {
    color: var(--semantic-success);
    background: var(--semantic-success-bg);
    border: 1px solid var(--semantic-success);
    animation: destelloSello 1s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .verificado .signo {
    display: inline-block;
    animation: aparecerSigno 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.15s both;
  }

  @keyframes destelloSello {
    from { box-shadow: 0 0 0 0 var(--color-emerald-glow); }
    50%  { box-shadow: 0 0 0 6px transparent; }
    to   { box-shadow: 0 0 0 0 transparent; }
  }

  @keyframes aparecerSigno {
    from { transform: scale(0.4); opacity: 0; }
    to   { transform: scale(1); opacity: 1; }
  }

  .generado    { color: var(--ink-secondary); background: var(--surface-panel); }
  .desconocido { color: var(--semantic-error); background: var(--semantic-error-bg); }
</style>
