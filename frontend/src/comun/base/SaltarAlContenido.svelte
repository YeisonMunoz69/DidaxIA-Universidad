
<script>
  let { destino = '#contenido', texto = 'Saltar al contenido' } = $props();
</script>

<a class="saltar" href={destino}>{texto}</a>

<style>
  .saltar {
    position: absolute;
    inset-block-start: 0;
    inset-inline-start: 0;
    z-index: 100;
    padding: 0.6em 1em;
    background: var(--surface-paper);
    color: var(--ink-primary);
    border-radius: 0 0 var(--radius-sm) 0;
    box-shadow: var(--shadow-soft);
    transform: translateY(-120%);
    transition: var(--transition-fast);
  }

  .saltar:focus-visible { transform: none; }
</style>
