
<script>
  let {
    texto = 'Este es un sistema automatizado. Lo que observa son indicios ' +
            'a partir de cómo escribes, no un diagnóstico, y puede ' +
            'equivocarse. Sirve para orientar el apoyo, no para evaluarte.'
  } = $props();
</script>

<aside class="aviso" role="note">
  <span class="signo" aria-hidden="true">i</span>
  <p>{texto}</p>
</aside>

<style>
  .aviso {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 8px 14px;
    background: var(--semantic-info-bg);
    border: 1px solid var(--semantic-info);
    border-radius: var(--radius-sm);
    margin-block-end: 1rem;
    max-inline-size: 100%;
  }

  .signo {
    flex: 0 0 1rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    block-size: 1rem;
    border-radius: 50%;
    background: var(--semantic-info);
    color: var(--surface-paper);
    font-size: 11px;
    font-weight: 700;
  }

  p {
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
    color: var(--ink-secondary);
    max-inline-size: 100%;
  }
</style>
