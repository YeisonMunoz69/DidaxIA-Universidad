
<script>
  let {
    forma = 'completa'
  } = $props();
</script>

{#if forma !== 'breve'}
  <section class="identidad">
    <h2>Asistente automatizado de cálculo diferencial</h2>
    <p>
      Esto no es una persona. Es un sistema que resuelve y explica derivadas
      con el material de tu curso, y que <strong>marca cada paso</strong> según
      lo haya comprobado con un motor matemático o lo haya redactado.
    </p>
    <p>
      Cuando no tiene material del curso que respalde algo, lo dice en vez de
      inventarlo. Si algo se sale del cálculo diferencial, te lo explica en
      lugar de intentar responderlo.
    </p>
  </section>
{/if}

<style>
  .identidad {
    padding: 12px 18px;
    background: var(--surface-panel);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    margin-block-end: 0.5rem;
    max-inline-size: 100%;
  }

  h2 {
    margin: 0 0 0.35rem;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  p {
    margin: 0 0 0.3rem;
    font-size: 12px;
    line-height: 1.45;
    color: var(--ink-secondary);
    max-inline-size: 100%;
  }

  p:last-child { margin-block-end: 0; }

  @media (max-width: 75rem) {
    .identidad {
      padding: 10px 14px;
    }
  }
</style>
