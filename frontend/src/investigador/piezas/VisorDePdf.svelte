
<script>
  let {
    documento = null,
    evidencia = 0,
    alto = '32rem'
  } = $props();

  let direccion = $state('');

  $effect(() => {
    if (!documento) {
      direccion = '';
      return;
    }
    const url = URL.createObjectURL(documento);
    direccion = url;
    return () => {
      URL.revokeObjectURL(url);
      direccion = '';
    };
  });

  const nombre = $derived(`evidencia-${Number(evidencia)}.pdf`);
</script>

{#if direccion}
  <object
    class="visor"
    data={direccion}
    type="application/pdf"
    style:block-size={alto}
    aria-label="Autorización del representante, evidencia {evidencia}"
  >

    <div class="sin-visor">
      <p>Este navegador no puede mostrar el documento aquí dentro.</p>
      <a href={direccion} target="_blank" rel="noopener noreferrer" download={nombre}>
        Abrir la autorización en otra pestaña
      </a>
    </div>
  </object>
{/if}

<style>
  .visor {
    inline-size: 100%;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-md);
    background: var(--surface-panel);
  }

  .sin-visor {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-xl);
    text-align: center;
  }

  .sin-visor p {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
  }

  .sin-visor a {
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--accent-main);
  }
</style>
