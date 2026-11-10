
<script>
  import Icono from "./Icono.svelte";

  let {
    abierto = $bindable(false),
    titulo,
    tipo = null,
    ancho = null,
    bloqueado = false,
    children,
    acciones,
    ...resto
  } = $props();

  let elemento = $state(null);
  const iconos = { descarga:'descargar', 'cerrar-sesion':'cerrar', eliminar:'eliminar', guardar:'guardar', confirmar:'check', comunicar:'correo' };
  let devolverFocoA = null;

  $effect(() => {
    if (!elemento) return;
    const nodo = elemento;
    if (abierto && !nodo.open) {
      devolverFocoA = document.activeElement;
      nodo.showModal();
    } else if (!abierto && nodo.open) {
      nodo.close();
    }

    const alHacerClic = (e) => {
      if (e.target === nodo) {
        const rect = nodo.getBoundingClientRect();
        const fuera =
          e.clientX < rect.left ||
          e.clientX > rect.right ||
          e.clientY < rect.top ||
          e.clientY > rect.bottom;
        if (fuera) {
          cerrar();
        }
      }
    };

    nodo.addEventListener("click", alHacerClic);
    return () => {
      nodo.removeEventListener("click", alHacerClic);
    };
  });

  function cerrar() {
    if (bloqueado) return;
    abierto = false;
    if (elemento && elemento.open) {
      elemento.close();
    }
    try {
      devolverFocoA?.focus?.();
    } catch {}
    devolverFocoA = null;
  }
</script>

<dialog
  bind:this={elemento}
  class:artesanal={Boolean(tipo)}
  class:descarga={tipo === 'descarga'}
  class:salida={tipo === 'cerrar-sesion'}
  class:eliminar={tipo === 'eliminar'}
  class:confirmar={tipo === 'confirmar'}
  class:guardar={tipo === 'guardar'}
  class:comunicar={tipo === 'comunicar'}
  aria-label={titulo}
  onclose={cerrar}
  oncancel={(e) => {
    e.preventDefault();
    cerrar();
  }}
  style={ancho
    ? `max-inline-size: min(${ancho}, calc(100vw - 2rem));`
    : undefined}
  {...resto}
>
  {#if tipo && iconos[tipo]}<div class="insignia" aria-hidden="true"><Icono nombre={iconos[tipo]} medida={28} /></div>{/if}
  <div class="cabecera-dialogo">
    <h2>{titulo}</h2>
    <button
      type="button"
      class="btn-cerrar-x"
      onclick={(e) => {
        e.stopPropagation();
        cerrar();
      }}
      disabled={bloqueado}
      aria-label="Cerrar ventana"
    >
      <Icono nombre="cerrar" medida={16} />
    </button>
  </div>
  <div class="cuerpo">{@render children?.()}</div>
  {#if acciones}<div class="acciones">{@render acciones()}</div>{/if}
</dialog>

<style>
  dialog:not([open]) {
    display: none !important;
  }

  dialog {
    max-inline-size: min(32rem, calc(100vw - 2rem));
    padding: 1.5rem;
    background: var(--surface-elevated);
    color: var(--ink-primary);
    border: 1px solid var(--trazo);
    border-color: var(--trazo);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
  }

  dialog::backdrop {
    background: var(--velo-modal);
    backdrop-filter: blur(2px);
  }

  .cabecera-dialogo {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
    margin-block-end: var(--espacio-sm);
  }

  h2 {
    font-size: var(--texto-lg);
    margin: 0;
    line-height: 1.25;
  }

  .btn-cerrar-x {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 32px;
    block-size: 32px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-xs);
    color: var(--ink-secondary);
    cursor: pointer;
    transition: var(--transition);
  }

  .btn-cerrar-x :global(svg) {
    stroke-width: 2.35px;
    transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .btn-cerrar-x:hover {
    background: var(--surface-canvas);
    border-color: var(--trazo-suave);
    color: var(--ink-primary);
  }

  .btn-cerrar-x:hover :global(svg) {
    transform: rotate(90deg) scale(1.12);
  }

  .acciones {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-block-start: 1.5rem;
  }
  dialog.artesanal { --tono-accion:var(--semantic-info); --fondo-accion:var(--semantic-info-bg); position:relative; display:flex; flex-direction:column; max-block-size:calc(100dvh - 3rem); overflow:visible; margin-block:auto; padding:2rem 1.5rem 1.5rem; border:2px solid var(--ink-primary); border-radius:255px 15px 225px 15px/15px 225px 15px 255px; box-shadow:4px 5px 0 var(--ink-primary); }
  dialog.artesanal .cuerpo { min-block-size:0; overflow:auto; }
  dialog.artesanal .acciones { flex:none; }
  dialog.artesanal.descarga { --tono-accion:var(--color-sky); --fondo-accion:var(--color-sky-bg); }
  dialog.artesanal.salida { --tono-accion:var(--semantic-warning); --fondo-accion:var(--semantic-warning-bg); }
  dialog.artesanal.eliminar { --tono-accion:var(--semantic-error); --fondo-accion:var(--semantic-error-bg); }
  dialog.artesanal.confirmar { --tono-accion:var(--semantic-success); --fondo-accion:var(--semantic-success-bg); }
  dialog.artesanal.guardar { --tono-accion:var(--semantic-success); --fondo-accion:var(--semantic-success-bg); }
  dialog.artesanal.comunicar { --tono-accion:var(--color-violet); --fondo-accion:var(--color-violet-bg); }
  .insignia { position:absolute; inset-block-start:-1.45rem; inset-inline-start:50%; transform:translateX(-50%); display:grid; place-items:center; inline-size:3rem; block-size:3rem; border:2px solid var(--ink-primary); border-radius:50%; background:var(--fondo-accion); color:var(--tono-accion); box-shadow:2px 2px 0 var(--ink-primary); }
  dialog.artesanal .cabecera-dialogo { margin-block-start:.5rem; }
  dialog.artesanal h2 { color:var(--tono-accion); }
  dialog.artesanal .acciones :global(button:last-child) { color:var(--surface-paper); background:var(--tono-accion); border:2px solid var(--ink-primary); box-shadow:2px 3px 0 var(--ink-primary); border-radius:255px 25px 225px 25px/25px 225px 25px 255px; transition:transform .15s,box-shadow .15s; }
  dialog.artesanal .acciones :global(button:last-child:active) { transform:translate(2px,3px); box-shadow:none; }
  dialog.artesanal .acciones :global(button.exito:last-child) { color:var(--semantic-success); background:var(--semantic-success-bg); border-color:var(--semantic-success); }
  @media(max-width:36rem) { dialog.artesanal { max-inline-size:calc(100vw - 2rem); } .acciones { flex-wrap:wrap; } }
  @media(prefers-reduced-motion:reduce) { dialog.artesanal .acciones :global(button:last-child) { transition:none; } }
</style>
