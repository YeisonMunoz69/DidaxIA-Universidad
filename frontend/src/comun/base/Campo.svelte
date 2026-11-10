
<script>
  let {
    etiqueta,
    valor = $bindable(''),
    tipo = 'text',
    multilinea = false,
    ayuda = '',
    error = '',
    requerido = false,
    id = 'campo-' + Math.random().toString(36).slice(2, 9),
    ...resto
  } = $props();

  const idAyuda = $derived(id + '-ayuda');
  const idError = $derived(id + '-error');
</script>

<div class="campo">
  <label for={id}>
    {etiqueta}
    {#if requerido}<span aria-hidden="true">&nbsp;*</span>
      <span class="solo-lectura-asistida">obligatorio</span>{/if}
  </label>

  {#if multilinea}
    <textarea
      {id}
      bind:value={valor}
      aria-describedby={ayuda ? idAyuda : undefined}
      aria-errormessage={error ? idError : undefined}
      aria-invalid={error ? 'true' : undefined}
      required={requerido}
      {...resto}></textarea>
  {:else}
    <input
      {id}
      type={tipo}
      bind:value={valor}
      aria-describedby={ayuda ? idAyuda : undefined}
      aria-errormessage={error ? idError : undefined}
      aria-invalid={error ? 'true' : undefined}
      required={requerido}
      {...resto} />
  {/if}

  {#if ayuda}<p class="ayuda" id={idAyuda}>{ayuda}</p>{/if}
  {#if error}<p class="error" id={idError}>{error}</p>{/if}
</div>

<style>
  .campo { display: flex; flex-direction: column; gap: 0.35em; }

  label { font-size: var(--texto-sm); font-weight: 500; }

  input, textarea {
    padding: 0.55em 0.75em;
    background: var(--surface-paper);
    border: 1px solid var(--trazo);
    border-color: var(--trazo);
    border-radius: var(--radius-trazado);
    color: var(--ink-primary);
  }

  textarea { min-block-size: 6em; resize: vertical; }

  input:hover, textarea:hover { border-color: var(--ink-tertiary); }

  [aria-invalid='true'] { border-color: var(--semantic-error); }

  .ayuda { font-size: var(--texto-sm); color: var(--ink-tertiary); margin: 0; }

  .error {
    font-size: var(--texto-sm);
    color: var(--semantic-error);
    margin: 0;
  }
  .error::before { content: '⚠ '; }
</style>
