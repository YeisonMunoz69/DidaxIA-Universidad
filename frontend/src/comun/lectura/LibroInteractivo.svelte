
<script>
  import Icono from '../base/Icono.svelte';
  import { onDestroy, onMount, tick } from 'svelte';
  import { prepararHoja } from './ondaDePapel.js';
  import { vigilarPapel } from './mallaDePapel.js';
  let {
    titulo = 'Lector',
    pagina = 1,
    total = 1,
    anterior = null,
    siguiente = null,
    alAnterior = null,
    alSiguiente = null,
    izquierda = null,
    derecha = null,
    simple = null,
    mostrarCabecera = true,
    variante = 'normal',
    unaPagina = false,
    mostrarControles = true,
    alDesplazar = null,
    identidad = null
  } = $props();

  let fase = $state('IDLE');
  let direccion = $state('siguiente');
  let progreso = $state(0);
  let torsion = $state(0);
  let origenX = 0;
  let origenY = 0;
  let ultimoX = 0;
  let ultimoTiempo = 0;
  let velocidad = 0;
  let puntero = null;
  let temporizador;
  let mesa;
  let onda;
  let destruido = false;
  onMount(() => vigilarPapel(mesa, () => !movimientoReducido()));
  onDestroy(() => { destruido = true; clearTimeout(temporizador); onda?.cancelar(); });
  let movil = $state(globalThis.matchMedia?.('(max-width: 47.999rem)').matches ?? false);

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(max-width: 47.999rem)');
    const actualizar = () => (movil = Boolean(consulta?.matches));
    consulta?.addEventListener?.('change', actualizar);
    return () => consulta?.removeEventListener?.('change', actualizar);
  });

  const movimientoReducido = () =>
    globalThis.document?.documentElement?.dataset.animaciones === 'no' ||
    (globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);

  function disponible(sentido) {
    return sentido === 'siguiente'
      ? Boolean(siguiente && alSiguiente)
      : Boolean(anterior && alAnterior);
  }

  function navegar(sentido) {
    return sentido === 'siguiente' ? alSiguiente?.() : alAnterior?.();
  }
  let identidadVista;
  $effect(() => {
    const actual = identidad ?? pagina;
    if (actual !== identidadVista) {
      identidadVista = actual;
      tick().then(() => mesa?.querySelectorAll('.contenido-pagina').forEach(nodo => {
        nodo.style.overflowAnchor = 'none';
        nodo.scrollTop = 0;
      }));
    }
  });
  async function pasar(sentido) {
    if (!disponible(sentido) || fase === 'SETTLING') return;
    direccion = sentido;
    fase = 'SETTLING'; progreso = 0; torsion = 0;
    clearTimeout(temporizador);
    await tick();
    if (destruido) return;
    const hoja = mesa?.querySelector(movil || unaPagina ? '.pagina-simple' : sentido === 'siguiente' ? '.pagina-derecha' : '.pagina-izquierda');
    onda?.cancelar();
    onda = movimientoReducido() ? null : prepararHoja(hoja,sentido);
    try {
      const resultado = await navegar(sentido);
      await tick();
      if (destruido) return;
      if (resultado === false || movimientoReducido()) {
        onda?.cancelar(); fase = 'IDLE'; return;
      }
      onda?.reproducir(() => { fase = 'IDLE'; progreso = 0; torsion = 0; });
    } catch {
      onda?.cancelar(); fase = 'IDLE';
    }
  }

  function alPulsar(evento) {
    if (fase !== 'IDLE' || evento.button !== 0) return;
    if (evento.target.closest('button, a, input, textarea, select, [contenteditable="true"]')) return;
    if (evento.pointerType === 'mouse') {
      const hoja = evento.target.closest('.pagina');
      const caja = hoja?.getBoundingClientRect();
      if (!caja || (evento.clientX > caja.left + 24 && evento.clientX < caja.right - 24)) return;
    }
    origenX = ultimoX = evento.clientX;
    origenY = evento.clientY;
    ultimoTiempo = performance.now();
    velocidad = 0;
    puntero = evento.pointerId;
  }

  function alMover(evento) {
    if (puntero !== evento.pointerId || fase === 'SETTLING') return;
    const dx = evento.clientX - origenX;
    const dy = evento.clientY - origenY;
    if (fase === 'IDLE') {
      if (Math.hypot(dx, dy) < 9) return;
      if (Math.abs(dy) >= Math.abs(dx) * 0.82) {
        puntero = null;
        return;
      }
      const sentido = dx < 0 ? 'siguiente' : 'anterior';
      if (!disponible(sentido)) { direccion = sentido; fase = 'DRAGGING'; progreso = .035; evento.currentTarget.setPointerCapture?.(evento.pointerId); return; }
      direccion = sentido;
      fase = 'DRAGGING';
      evento.currentTarget.setPointerCapture?.(evento.pointerId);
    }
    evento.preventDefault();
    const ancho = Math.max(evento.currentTarget.clientWidth * 0.48, 180);
    const avance = direccion === 'siguiente' ? -dx : dx;
    progreso = disponible(direccion) ? Math.max(0, Math.min(1, avance / ancho)) : Math.min(.06, Math.abs(dx) / (ancho * 8));
    torsion = Math.max(-2.2, Math.min(2.2, dy / 36));
    const ahora = performance.now();
    velocidad = (evento.clientX - ultimoX) / Math.max(ahora - ultimoTiempo, 1);
    ultimoX = evento.clientX;
    ultimoTiempo = ahora;
  }

  function terminar(evento) {
    if (puntero !== evento.pointerId) return;
    puntero = null;
    if (fase !== 'DRAGGING') return;
    evento.currentTarget.releasePointerCapture?.(evento.pointerId);
    const impulso = direccion === 'siguiente' ? -velocidad : velocidad;
    if (disponible(direccion) && (progreso >= 0.34 || impulso > 0.48)) {
      pasar(direccion);
      return;
    }
    fase = 'SETTLING';
    progreso = 0;
    torsion = 0;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => (fase = 'IDLE'), 260);
  }

  function alTeclar(evento) {
    if (evento.target.closest('button, a, input, textarea, select, [contenteditable="true"]')) return;
    if (evento.key === 'ArrowRight' || evento.key === 'PageDown') {
      evento.preventDefault();
      pasar('siguiente');
    } else if (evento.key === 'ArrowLeft' || evento.key === 'PageUp') {
      evento.preventDefault();
      pasar('anterior');
    }
  }

  const giro = $derived((direccion === 'siguiente' ? -180 : 180) * progreso);
  const sombra = $derived(Math.sin(Math.PI * progreso));
  const avance = $derived(total > 1 ? ((pagina - 1) / (total - 1)) * 100 : 100);
</script>



<div
  class="lector"
  class:arrastrando={fase === 'DRAGGING'}
  class:acomodando={fase === 'SETTLING'}
  class:hacia-atras={direccion === 'anterior'}
  class:sin-cabecera={!mostrarCabecera}
  class:lector-conceptos={variante === 'conceptos'}
  class:una-pagina={unaPagina}
  style:--giro={`${giro}deg`}
  style:--torsion={`${torsion}deg`}
  style:--sombra={sombra}
  style:--avance={`${avance}%`}
  aria-label={titulo}
  role="region"
  data-fase={fase}
  tabindex="0"
  onkeydown={alTeclar}
  onpointerdown={alPulsar}
  onpointermove={alMover}
  onpointerup={terminar}
  onpointercancel={(evento) => { puntero = null; if (fase === 'DRAGGING') { progreso = 0; torsion = 0; fase = 'IDLE'; } evento.currentTarget.releasePointerCapture?.(evento.pointerId); }}
>
  {#if mostrarCabecera}
    <header class="barra-lectura">
      <span class="titulo-lectura">{titulo}</span>
      <span class="gesto-lectura" aria-hidden="true">Desliza o usa las flechas para pasar</span>
    </header>
  {/if}

  <div class="mesa" bind:this={mesa}>
    <button class="margen-pagina margen-anterior" type="button" disabled={!anterior || fase === 'SETTLING'}
            aria-label={anterior ? `Pasar hacia atrás: ${anterior}` : 'Pasar hacia atrás'} onclick={() => pasar('anterior')}>
      <Icono nombre="flecha-izq" medida={24} />
    </button>
    {#if movil || unaPagina}
    <article class="pagina pagina-simple simple">
      <div class="contenido-pagina" onscroll={(evento) => alDesplazar?.(evento)}>{@render simple?.()}</div>
      <span class="folio" aria-hidden="true">{pagina}</span>
    </article>
    {:else}
    <div class="pliego doble">
      <article class="pagina pagina-izquierda">
        <div class="contenido-pagina" onscroll={(evento) => alDesplazar?.(evento)}>{@render izquierda?.()}</div>
        <span class="folio folio-izquierdo" aria-hidden="true">{pagina}</span>
      </article>
      <article class="pagina pagina-derecha">
        <div class="contenido-pagina" onscroll={(evento) => alDesplazar?.(evento)}>{@render derecha?.()}</div>
        <span class="folio folio-derecho" aria-hidden="true">{pagina}</span>
      </article>
      <div class="lomo" aria-hidden="true"></div>
    </div>
    {/if}
    <button class="margen-pagina margen-siguiente" type="button" disabled={!siguiente || fase === 'SETTLING'}
            aria-label={siguiente ? `Pasar hacia delante: ${siguiente}` : 'Pasar hacia delante'} onclick={() => pasar('siguiente')}>
      <Icono nombre="flecha-der" medida={24} />
    </button>
  </div>

  {#if mostrarControles}<footer class="controles-libro" aria-label="Navegación del libro">
    <button type="button" disabled={!anterior || fase === 'SETTLING'} aria-label={anterior ? `Anterior: ${anterior}` : 'Anterior'} onclick={() => pasar('anterior')}>
      <span aria-hidden="true">←</span><span class="nombre-adyacente">{anterior || 'Anterior'}</span>
    </button>
    <span class="progreso-libro" aria-label={`Página ${pagina} de ${total}`}>
      <span>{pagina}</span><i aria-hidden="true"><b></b></i><span>{total}</span>
    </span>
    <button type="button" disabled={!siguiente || fase === 'SETTLING'} aria-label={siguiente ? `Siguiente: ${siguiente}` : 'Siguiente'} onclick={() => pasar('siguiente')}>
      <span class="nombre-adyacente">{siguiente || 'Siguiente'}</span><span aria-hidden="true">→</span>
    </button>
  </footer>{/if}
</div>

<style>
  .lector {
    --giro: 0deg;
    --torsion: 0deg;
    --sombra: 0;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: .55rem;
    inline-size: 100%;
    block-size: 100%;
    min-block-size: 0;
    perspective: 2200px;
  }

  .lector.sin-cabecera { grid-template-rows: minmax(0, 1fr) auto; }

  .lector:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 3px;
    border-radius: var(--radius-md);
  }

  .barra-lectura {
    min-block-size: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: var(--ink-tertiary);
    font-size: .7rem;
    letter-spacing: .025em;
  }

  .titulo-lectura {
    max-inline-size: min(65%, 34rem);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--ink-secondary);
    font-weight: 700;
  }

  .gesto-lectura { opacity: .72; }

  .mesa {
    perspective: 2200px;
    position: relative;
    min-block-size: 0;
    display: grid;
    place-items: stretch center;
    padding: clamp(.45rem, 1.4vw, 1rem) clamp(1.8rem, 5vw, 4.5rem);
    border-radius: clamp(1rem, 2.5vw, 1.8rem);
    background:
      radial-gradient(ellipse at 50% 96%, color-mix(in srgb, var(--accent-main) 8%, transparent), transparent 52%),
      linear-gradient(145deg, color-mix(in srgb, var(--surface-canvas) 88%, var(--book-desk-tint)), var(--surface-canvas));
    overflow: hidden;
  }

  .pliego {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    inline-size: min(100%, 68rem);
    block-size: 100%;
    min-block-size: 0;
    filter: drop-shadow(0 18px 22px color-mix(in srgb, var(--ink-primary) 16%, transparent));
    transform-style: preserve-3d;
  }

  .pagina {
    position: relative;
    min-inline-size: 0;
    min-block-size: 0;
    margin: 0;
    overflow: hidden;
    --papel-lectura: var(--book-paper);
    color: var(--ink-primary);
    background:
      linear-gradient(90deg, var(--book-paper-grain), transparent 12%, transparent 88%, var(--book-paper-grain)),
      var(--papel-lectura);
    border: 1px solid var(--trazo-suave);
    transform-style: preserve-3d;
    backface-visibility: hidden;

  }

  .pagina-izquierda {
    border-radius: 10px 2px 2px 10px;
    border-inline-end: 0;
    box-shadow: inset -26px 0 34px -34px var(--ink-primary), inset 1px 0 var(--book-page-glint);
  }

  .pagina-derecha {
    border-radius: 2px 10px 10px 2px;
    transform-origin: left center;
    box-shadow: inset 26px 0 34px -34px var(--ink-primary), inset -1px 0 var(--book-page-glint);
  }

  .pagina::after {
    content: '';
    position: absolute;
    z-index: 20;
    inset: 0;
    opacity: var(--sombra);
    pointer-events: none;
    background: linear-gradient(90deg, var(--book-turn-shadow), transparent 22%, transparent 72%, var(--book-turn-shadow-soft));
  }

  .pagina::before {
    content: '';
    position: absolute;
    z-index: 21;
    inset-block: 0;
    inset-inline-end: 0;
    inline-size: 22%;
    opacity: calc(var(--sombra) * .9);
    pointer-events: none;
    background: linear-gradient(90deg, transparent, var(--book-page-glint) 48%, var(--book-turn-shadow-soft));
    transform: translateX(calc((1 - var(--sombra)) * 100%));
  }

  .pagina-izquierda::after { background: linear-gradient(270deg, var(--book-turn-shadow), transparent 25%); }

  .lector:not(.hacia-atras) .pagina-derecha {
    z-index: 3;
    transform: translateX(calc(var(--sombra) * -7px)) rotateY(var(--giro)) rotateZ(var(--torsion));
    filter: brightness(calc(1 - var(--sombra) * .12));
    box-shadow:
      inset 20px 0 28px -28px var(--ink-tertiary),
      calc(var(--sombra) * -28px) 11px 34px color-mix(in srgb, var(--ink-primary) 26%, transparent);
  }

  .lector.hacia-atras .pagina-izquierda {
    z-index: 3;
    transform-origin: right center;
    transform: translateX(calc(var(--sombra) * 7px)) rotateY(var(--giro)) rotateZ(var(--torsion));
    filter: brightness(calc(1 - var(--sombra) * .12));
  }

  .acomodando .pagina-derecha,
  .acomodando .pagina-izquierda,
  .acomodando .pagina-simple {
    transition: transform 420ms cubic-bezier(.22,.78,.18,1), filter 420ms ease, box-shadow 420ms ease;
  }


  .contenido-pagina {
    block-size: 100%;
    min-block-size: 0;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    scrollbar-width: thin;
    scrollbar-color: color-mix(in srgb, var(--ink-tertiary) 35%, transparent) transparent;
    touch-action: pan-y pinch-zoom;
    -webkit-overflow-scrolling: touch;
    padding-block-end: 1.7rem;
    box-sizing: border-box;
  }

  .lector-conceptos .mesa {
    padding-block: clamp(.7rem, 1.7vw, 1.25rem);
    background:
      radial-gradient(ellipse at 50% 102%, color-mix(in srgb, var(--ink-primary) 10%, transparent), transparent 46%),
      linear-gradient(150deg, color-mix(in srgb, var(--surface-canvas) 94%, var(--book-desk-tint)), var(--surface-canvas));
  }

  .lector-conceptos .pliego, .lector-conceptos.una-pagina .simple { inline-size: 100%; }
  .lector-conceptos .mesa { padding: 0; background: transparent; border-radius: 0; }
  .lector-conceptos .pagina { border: 0; }

  .lector-conceptos .pagina {
    border-color: color-mix(in srgb, var(--trazo-suave) 78%, transparent);
  }

  .lector-conceptos .controles-libro {
    min-block-size: 34px;
    padding-inline: clamp(.4rem, 3vw, 2rem);
  }

  .contenido-pagina :global(.detalle-concepto) { background: transparent; }
  .contenido-pagina :global(.contenido-seccion),
  .contenido-pagina :global(.texto) {
    font-family: ui-serif, Georgia, Cambria, 'Times New Roman', serif;
    line-height: 1.72;
  }

  .lomo {
    position: absolute;
    z-index: 6;
    inset-block: 0;
    inset-inline-start: 50%;
    inline-size: 3px;
    transform: translateX(-50%);
    background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--ink-primary) 25%, transparent), transparent);
    box-shadow: 0 0 24px 8px color-mix(in srgb, var(--ink-primary) 10%, transparent);
    pointer-events: none;
  }

  .simple { display: none; }
  .una-pagina .simple {
    display: block;
    inline-size: min(100%, 52rem);
    block-size: 100%;
    border-radius: 4px 12px 12px 4px;
    box-shadow: inset 8px 0 16px -16px var(--ink-primary), 0 16px 34px var(--book-cover-shadow);
  }
  .acomodando .pagina { transform: none !important; transition: none; }

  .folio {
    position: absolute;
    z-index: 22;
    inset-block-end: .55rem;
    inset-inline-start: 50%;
    transform: translateX(-50%);
    color: var(--ink-tertiary);
    font: 500 .66rem/1 ui-serif, Georgia, serif;
    pointer-events: none;
  }

  .folio-izquierdo { inset-inline-start: auto; inset-inline-end: 1.2rem; transform: none; }
  .folio-derecho { inset-inline-start: 1.2rem; transform: none; }

  .margen-pagina {
    position: absolute;
    z-index: 12;
    inset-block: 42% auto;
    inline-size: 44px;
    block-size: 54px;
    display: grid;
    place-items: center;
    padding: 0;
    border: 2px solid var(--accent-main);
    border-radius: var(--radius-sm);
    background: var(--surface-paper);
    color: var(--accent-main);
    box-shadow: var(--shadow-soft);
    font: 300 2rem/1 ui-serif, Georgia, serif;
    cursor: pointer;
    opacity: 1;
    backdrop-filter: blur(10px);
    transition: opacity .2s ease, transform .2s ease, background .2s ease;
  }

  .margen-anterior { inset-inline-start: .45rem; }
  .margen-siguiente { inset-inline-end: .45rem; }
  .margen-pagina:hover:not(:disabled), .margen-pagina:focus-visible { opacity: 1; background: var(--surface-panel); transform: scale(1.06); }
  .margen-pagina:disabled { opacity: .35; pointer-events: none; }

  .controles-libro {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center;
    gap: .8rem;
    padding-inline: .3rem;
  }

  .controles-libro button {
    justify-self: start;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-block-size: 44px;
    max-inline-size: 100%;
    padding: 0.45rem 0.75rem;
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-sm);
    background: var(--accent-surface);
    color: var(--accent-main);
    font: inherit;
    font-size: var(--texto-xs);
    font-weight: 650;
    cursor: pointer;
    box-shadow: none;
  }

  .controles-libro button:last-child { justify-self: end; }
  .controles-libro button:hover:not(:disabled) { color: var(--accent-main); background: var(--accent-surface); }
  .controles-libro button:disabled { opacity: .38; cursor: default; }

  .nombre-adyacente {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .progreso-libro {
    display: grid;
    grid-template-columns: auto minmax(5rem, 12rem) auto;
    align-items: center;
    gap: .45rem;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    font-variant-numeric: tabular-nums;
  }

  .progreso-libro i { position: relative; block-size: 3px; overflow: hidden; background: var(--trazo); border-radius: 999px; }
  .progreso-libro i b { position: absolute; inset: 0 auto 0 0; inline-size: var(--avance); border-radius: inherit; background: var(--accent-main); transition: inline-size .35s cubic-bezier(.22,1,.36,1); }

  @media (max-width: 47.999rem) {
    .controles-libro button { min-block-size: 44px; min-inline-size: 44px; }
    .doble { display: none; }
    .simple {
      display: block;
      inline-size: min(100%, 42rem);
      block-size: 100%;
      justify-self: center;
      border-radius: 9px;
      transform-origin: left center;
      transform: translateX(calc(var(--sombra) * -5px)) rotateY(var(--giro)) rotateZ(var(--torsion));
      filter: brightness(calc(1 - var(--sombra) * .1));
      box-shadow: 0 18px 34px color-mix(in srgb, var(--ink-primary) 16%, transparent);
    }
    .lector.hacia-atras .pagina-simple { transform-origin: right center; }
    .mesa { padding: .35rem .45rem; border-radius: .9rem; }
    .barra-lectura { justify-content: space-between; padding-inline: .25rem; }
    .gesto-lectura { display: none; }
    .titulo-lectura { max-inline-size: 100%; }
    .lector-conceptos.sin-cabecera { grid-template-rows: minmax(0,1fr); gap: 0; }
    .margen-pagina { inset-block-start: 45%; inline-size: 44px; block-size: 48px; opacity: 1; }
    .margen-anterior { inset-inline-start: .15rem; }
    .margen-siguiente { inset-inline-end: .15rem; }
    .nombre-adyacente { display: none; }
    .progreso-libro { grid-template-columns: auto minmax(4rem, 8rem) auto; }
  }

  @media (prefers-reduced-motion: reduce) {
    .pagina { transition: none !important; }
  }
</style>
