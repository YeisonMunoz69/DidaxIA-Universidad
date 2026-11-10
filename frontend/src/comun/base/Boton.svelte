<!--
Envuelve <button>.

DD-05 decidió HTML nativo primero. Este componente NO reimplementa nada:
envuelve el elemento que ya significa lo que se quiere decir y le pone el
estilo del sistema. Nunca un div con manejador de clic.

Un <div> con onclick no recibe foco, no responde a Espacio ni a Intro, y no
se anuncia como botón. Esas tres cosas las trae <button> de serie, y
recuperarlas a mano son veinte líneas que siempre salen mal.



-->
<script>
  let {
    tipo = 'button',
    variante = 'principal',   // principal · secundario · discreto
    deshabilitado = false,
    href = null,
    children,
    ...resto
  } = $props();
</script>

{#if href}
<a {href} class="boton {variante}" {...resto}>
  {@render children?.()}
</a>
{:else}
<button type={tipo} class="boton {variante}" disabled={deshabilitado} {...resto}>
  {@render children?.()}
</button>
{/if}

<style>
  /*
    CAJA TRAZADA, NO CALCULADA. Las cuatro esquinas llevan radio distinto
    —`--radius-trazado`— y ése es todo el truco: basta esa asimetría de dos o
    tres píxeles para que la caja se lea como dibujada. Sin gradiente y sin
    sombra fuerte, que el lenguaje prohíbe los dos.
  */
  .boton {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5em;
    padding: 0.55em 1.1em;
    border: 1px solid transparent;
    border-radius: var(--radius-trazado);
    font-size: var(--texto-base);
    font-weight: 500;
    line-height: 1.2;
    text-decoration: none;
    transition: var(--transition-fast);
  }

  .principal  { background: var(--accent-main); color: var(--surface-paper); }

  /*
    EL BORDE PASA DE `--ink-ghost` A `--trazo`, Y NO ES UN CAMBIO DE TONO.

    `--ink-ghost` está declarado como decoración y el comprobador lo EXIME del
    mínimo de contraste. Un borde que es lo único que delimita un botón no es
    decoración: `WCAG 2.2 · 1.4.11` le pide 3.0, y con el token exento podía
    bajar de ahí sin que nada lo dijera. `--trazo` existe para esto y se mide.
  */
  .secundario { background: var(--surface-paper); color: var(--ink-primary);
                border-color: var(--trazo); }
  .discreto   { background: transparent; color: var(--ink-secondary); }
  .exito { background: var(--semantic-success-bg); color: var(--semantic-success); border-color: var(--semantic-success); }

  .boton {
    transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .principal:hover:not(:disabled)  {
    background: var(--accent-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--accent-glow);
  }
  .secundario:hover:not(:disabled) {
    background: var(--surface-panel);
    transform: translateY(-1px);
    box-shadow: var(--shadow-soft);
  }
  /* El borde que APARECE al pasar por encima delimita un control, así que le
     toca `--trazo` y no `--trazo-suave`: con el suave daba 1.80 sobre la mesa
     y 1.68 en el tema oscuro, muy por debajo del 3.0 de `WCAG 2.2 · 1.4.11`.
     Es exactamente la confusión que el token nuevo vino a deshacer. */
  .discreto:hover:not(:disabled)   { color: var(--ink-primary);
                                     border-color: var(--trazo);
                                     background: var(--accent-surface); }

  /* Pulsado. */
  .boton:active:not(:disabled) { transform: translateY(0) scale(0.97); }

  /* Deshabilitado se marca con opacidad Y con el cursor: la opacidad sola
     puede dejar el texto por debajo del contraste exigido. */
  .boton:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
