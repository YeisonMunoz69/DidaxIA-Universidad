
<script>
  import Icono from '../base/Icono.svelte';

  let {
    icono,
    titulo,
    children
  } = $props();
</script>

<div class="bloqueo-autenticacion" role="region" aria-label="Inicio de sesión">
  <div class="tarjeta-bloqueo">
    <Icono nombre={icono} medida={36} />
    <h2>{titulo}</h2>
    {@render children?.()}
  </div>
</div>

<style>
  .bloqueo-autenticacion {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2.5rem 1rem;
    margin: auto 0;
  }

  .tarjeta-bloqueo {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    max-inline-size: 460px;
    padding: 2.2rem 1.8rem;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
    gap: 0.85rem;
  }

  .tarjeta-bloqueo h2 {
    font-size: var(--texto-lg);
    font-weight: 600;
    color: var(--ink-primary);
    margin: 0;
  }

  .tarjeta-bloqueo :global(p) {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    line-height: 1.5;
    margin: 0;
  }
</style>
