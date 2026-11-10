<!--
Envuelve <input> o <textarea>.

DD-05 decidió HTML nativo primero. Con su <label> asociada DE VERDAD por
`for`/`id`, no colocada al lado. Una etiqueta puesta cerca se ve bien y no
existe para un lector de pantalla: al llegar al campo, este se anuncia sin
nombre y el usuario no sabe qué escribir.

El identificador se genera si no se pasa, para que la asociación no dependa
de que alguien se acuerde de inventar uno único.

El texto de error se asocia con `aria-errormessage` y el campo se marca con
`aria-invalid`. Pintar el borde de rojo no comunica nada a quien no lo ve.



-->
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

  // $derived y no const: `id` es una prop y puede cambiar. Con `const` se
  // capturaría el valor inicial y la asociación label/campo se rompería en
  // silencio, que es justo el fallo que este componente existe para evitar.
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

  /*
    CAJA ESCRITA CON MARCADOR, Y EL BORDE ACTIVO NUNCA SE OCULTA.

    El borde pasa de `--ink-ghost` a `--trazo` por lo mismo que en `Boton`:
    `--ink-ghost` está declarado decoración y el comprobador lo exime del
    mínimo, pero aquí el borde es lo ÚNICO que dice dónde empieza el campo.
    `WCAG 2.2 · 1.4.11` le pide 3.0 y con el token exento nadie lo medía.
  */
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

  /* El error lleva su propio símbolo además del color, porque el color solo
     no distingue nada para quien no lo percibe. */
  .error {
    font-size: var(--texto-sm);
    color: var(--semantic-error);
    margin: 0;
  }
  .error::before { content: '⚠ '; }
</style>
