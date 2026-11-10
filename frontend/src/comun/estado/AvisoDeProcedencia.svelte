
<script>
  let {
    procedencia
  } = $props();
</script>

{#if procedencia?.origen === 'sin-fuente'}
  <span class="procedencia sin-fuente">
    <span class="signo" aria-hidden="true">!</span>
    Sin material del curso que lo respalde
  </span>
{:else if procedencia?.origen === 'corpus'}
  <span class="procedencia corpus">
    <span class="signo" aria-hidden="true">§</span>

    Material del curso{!procedencia.material?.length && procedencia.referencia
      ? ' · ' + procedencia.referencia : ''}
  </span>
{/if}

<style>
  .procedencia {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    font-size: var(--texto-xs);
  }

  .signo { font-weight: 700; }

  .corpus { color: var(--ink-tertiary); }

  .sin-fuente {
    color: var(--semantic-warning);
    font-weight: 500;
    padding: 0.15em 0.45em;
    background: var(--semantic-warning-bg);
    border-radius: var(--radius-xs);
  }
</style>
