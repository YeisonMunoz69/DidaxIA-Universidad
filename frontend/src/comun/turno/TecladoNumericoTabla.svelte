<script>
  import { onMount } from 'svelte';

  let { etiqueta, valor = $bindable(''), error = '', alAplicar, alCancelar } = $props();
  let panel;
  let reemplazar = true;
  let cursorVisible = $state(false);
  let inicio = $state(0);
  let fin = $state(0);

  onMount(() => { situar(valor.length); panel?.focus(); });

  function situar(cursor) {
    inicio = cursor;
    fin = cursor;
  }

  function mover(direccion) {
    const posicion = reemplazar ? valor.length : inicio;
    reemplazar = false;
    cursorVisible = true;
    situar(Math.max(0, Math.min(valor.length, posicion + direccion)));
  }

  function pulsar(tecla) {
    const antes = reemplazar ? '' : valor.slice(0, inicio);
    const despues = reemplazar ? '' : valor.slice(fin);
    let cursor = inicio;
    if (tecla === 'borrar') {
      if (reemplazar) { valor = ''; cursor = 0; }
      else if (inicio !== fin) { valor = antes + despues; }
      else if (inicio > 0) { valor = valor.slice(0, inicio - 1) + valor.slice(fin); cursor--; }
    } else if (tecla === 'limpiar') {
      valor = '';
      cursor = 0;
    } else if (tecla === 'signo') {
      valor = valor.startsWith('-') ? valor.slice(1) : `-${valor}`;
      cursor = Math.max(0, Math.min(valor.length, inicio + (valor.startsWith('-') ? 1 : -1)));
    } else if (tecla === ',') {
      if (!/[.,]/.test(valor)) {
        const prefijo = reemplazar || !valor ? '0' : antes;
        valor = `${prefijo},${despues}`;
        cursor = prefijo.length + 1;
      }
    } else {
      valor = antes + tecla + despues;
      cursor = antes.length + 1;
    }
    reemplazar = false;
    cursorVisible = true;
    situar(cursor);
  }

  function alTeclado(evento) {
    if (/^\d$/.test(evento.key)) pulsar(evento.key);
    else if (evento.key === ',' || evento.key === '.') pulsar(',');
    else if (evento.key === '-') pulsar('signo');
    else if (evento.key === 'ArrowLeft') mover(-1);
    else if (evento.key === 'ArrowRight') mover(1);
    else if (evento.key === 'Backspace') pulsar('borrar');
    else if (evento.key === 'Delete') pulsar('limpiar');
    else if (evento.key === 'Enter') alAplicar();
    else if (evento.key === 'Escape') alCancelar();
    else return;
    evento.preventDefault();
  }
</script>

<dialog open class="teclado-numerico-tabla" aria-label={`Editar ${etiqueta}`}
         tabindex="-1" bind:this={panel} onkeydown={alTeclado}>
  <div class="cabecera-teclado">
    <strong>{etiqueta}</strong>
    <button type="button" aria-label="Cerrar teclado numérico" onclick={alCancelar}>×</button>
  </div>
  <div class="envoltura-pantalla" class:con-cursor={cursorVisible}>
    <output class="pantalla-numero" aria-label={`Valor de ${etiqueta}`}>
      {#if valor}<span>{valor.slice(0, inicio)}</span>{#if cursorVisible}<i class="marca-cursor" aria-hidden="true"></i>{/if}<span>{valor.slice(inicio)}</span>{:else}<span class="placeholder">Escribe un número</span>{/if}
    </output>
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <div class="navegacion" role="group" aria-label="Mover el cursor">
    <button type="button" aria-label="Mover cursor a la izquierda" onclick={() => mover(-1)}>←</button>
    <button type="button" aria-label="Mover cursor a la derecha" onclick={() => mover(1)}>→</button>
  </div>
  <div class="teclas" role="group" aria-label="Números y coma decimal">
    {#each ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'signo', '0', ','] as tecla}
      <button type="button" aria-label={tecla === 'signo' ? 'Cambiar signo' : tecla === ',' ? 'Coma decimal' : tecla}
              onclick={() => pulsar(tecla)}>{tecla === 'signo' ? '±' : tecla}</button>
    {/each}
  </div>
  <div class="acciones">
    <button type="button" onclick={() => pulsar('limpiar')}>Borrar todo</button>
    <button type="button" onclick={() => pulsar('borrar')} aria-label="Borrar dígito anterior al cursor">⌫</button>
    <button type="button" class="aplicar" onclick={alAplicar}>Aplicar</button>
  </div>
</dialog>

<style>
  .teclado-numerico-tabla { position: absolute; z-index: 21; inset-inline: .5rem; inset-block-end: calc(4.1rem + env(safe-area-inset-bottom)); display: grid; gap: .45rem; max-inline-size: 24rem; margin-inline: auto; padding: .65rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-lg); background: var(--surface-panel); color: var(--ink-primary); box-shadow: var(--shadow-float); }
  .teclado-numerico-tabla:focus { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .cabecera-teclado, .acciones { display: flex; justify-content: space-between; align-items: center; gap: .4rem; }
  .cabecera-teclado button { min-inline-size: 36px; }
  .envoltura-pantalla { position: relative; }
  .pantalla-numero { display: block; inline-size: 100%; min-block-size: 2.3rem; padding: .35rem .55rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-variant-numeric: tabular-nums; text-align: end; caret-color: var(--accent-main); cursor: text; }
  .pantalla-numero { display: flex; justify-content: flex-end; align-items: center; overflow: hidden; }
  .placeholder { color: var(--ink-tertiary); }
  .navegacion { display: flex; gap: .3rem; }
  .navegacion button { flex: 1; }
  .marca-cursor { flex: none; inline-size: 2px; block-size: 1.2em; background: var(--help-color); }
  .teclas { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .25rem; }
  button { min-block-size: 38px; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; cursor: pointer; }
  button:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 1px; }
  .acciones button { flex: 1; }
  .acciones .aplicar { background: var(--accent-surface); border-color: var(--accent-main); color: var(--accent-main); font-weight: 750; }
  .error { margin: 0; color: var(--semantic-error); font-size: var(--texto-xs); }
</style>
