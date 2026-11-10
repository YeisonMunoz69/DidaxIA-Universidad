
<script>
  let {
    titulo,
    children
  } = $props();
</script>

<div class="aviso-pendiente" role="note">
  <strong>{titulo}</strong>
  <p>{@render children?.()}</p>
</div>

<style>
  .aviso-pendiente {
    padding: var(--espacio-md) var(--espacio-lg);
    background: var(--semantic-warning-bg);
    border: 1px solid var(--semantic-warning);
    border-radius: var(--radius-md);
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .aviso-pendiente strong { display: block; color: var(--ink-primary); margin-block-end: 0.25rem; }

  .aviso-pendiente p { margin: 0; max-inline-size: none; line-height: 1.5; }

  .aviso-pendiente :global(code) {
    font-family: var(--fuente-mono);
    font-size: 0.92em;
    background: var(--surface-paper);
    padding: 0.1em 0.35em;
    border-radius: var(--radius-xs);
  }
</style>
