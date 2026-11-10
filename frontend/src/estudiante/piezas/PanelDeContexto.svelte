
<script>
  import Icono from '../../comun/base/Icono.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import PanelDeConceptos from '../../comun/concepto/PanelDeConceptos.svelte';
  import FichaDeConcepto from '../../comun/concepto/FichaDeConcepto.svelte';
  import GaleriaDeTrabajo from './GaleriaDeTrabajo.svelte';
  import * as bancoDeConceptos from '../../nucleo/api/conceptos.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { conceptosDelHilo } from '../../nucleo/presentacion/materialDelHilo.js';

  let {
    hilo,
    solicitudGrafica = null,
    alCerrarGraficaDelChat = null,
    visibleEnEscritorio = true,
    editando = false,
    soloLectura = false
  } = $props();

  let abiertoMovil = $state(false);
  let esMovil = $state(
    globalThis.matchMedia?.('(max-width: 48rem)').matches ?? false
  );
  let panel = $state(null);
  let activador = $state(null);

  $effect(() => {
    if (solicitudGrafica && esMovil) abiertoMovil = true;
  });

  function cerrarTrasGraficaDelChat() {
    if (esMovil) abiertoMovil = false;
    alCerrarGraficaDelChat?.();
  }

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(max-width: 48rem)');
    const alCambiar = () => {
      esMovil = Boolean(consulta?.matches);
      if (!esMovil) abiertoMovil = false;
    };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  $effect(() => {
    if (!abiertoMovil || !esMovil) return;
    const alTeclear = (evento) => {
      if (evento.key === 'Escape'
        && !evento.defaultPrevented
        && !evento.didaxiaDialogo
        && !globalThis.document?.querySelector('[role="dialog"][aria-modal="true"]')) {
        cerrarEnMovil();
      }
    };
    globalThis.addEventListener?.('keydown', alTeclear);
    globalThis.requestAnimationFrame?.(() => panel?.focus());
    return () => globalThis.removeEventListener?.('keydown', alTeclear);
  });

  function abrirEnMovil() {
    abiertoMovil = true;
  }

  function cerrarEnMovil() {
    abiertoMovil = false;
    globalThis.requestAnimationFrame?.(() => activador?.focus());
  }

  let ficha = $state(null);
  let fichaAbierta = $state(false);
  let falloDeFicha = $state(null);

  async function abrirConcepto(id) {
    falloDeFicha = null;
    try {
      ficha = await bancoDeConceptos.ficha(id);
      fichaAbierta = true;
    } catch (e) {
      ficha = null;
      falloDeFicha = describir(e);
      fichaAbierta = true;
    }
  }

  const conceptos = $derived(conceptosDelHilo(hilo));
</script>

<button
  type="button"
  class="abrir-panel-movil"
  class:oculto-al-escribir={editando}
  aria-controls="panel-contexto-conversacion"
  aria-expanded={abiertoMovil}
  bind:this={activador}
  onclick={abrirEnMovil}>
  <Icono nombre="conceptos" medida={17} />
  <span>Conceptos y gráficas</span>
</button>

<aside
  id="panel-contexto-conversacion"
  class="panel"
  class:oculto-escritorio={!visibleEnEscritorio && !solicitudGrafica}
  class:abierto-movil={abiertoMovil}
  aria-label="Contexto de la conversación"
  aria-hidden={esMovil && !abiertoMovil ? 'true' : undefined}
  inert={esMovil && !abiertoMovil ? true : undefined}
  tabindex="-1"
  bind:this={panel}>
  <div class="cabecera-panel-der">
    <div class="titular-panel">
      <Icono nombre="conceptos" medida={17} />
      <h2>Conceptos y Recursos</h2>
    </div>
    <button
      type="button"
      class="cerrar-panel-movil"
      aria-label="Volver a la conversación"
      onclick={cerrarEnMovil}>
      <Icono nombre="cerrar" medida={18} />
    </button>
  </div>

  <div class="cuerpo-panel-der">
    <GaleriaDeTrabajo {hilo} {solicitudGrafica} {soloLectura} alCerrarDesdeChat={cerrarTrasGraficaDelChat} />

    {#if conceptos.length}
      <PanelDeConceptos {conceptos} alAbrir={abrirConcepto} />
    {:else}
      <div class="tarjeta-vacia-panel">
        <div class="icono-vacio">
          <Icono nombre="conceptos" medida={28} />
        </div>
        <h3 class="titulo-vacio-panel">Material de Apoyo</h3>
        <p class="sin-conceptos">
          Aquí aparecerán de forma automática las gráficas dinámicas, fórmulas de derivadas y conceptos pedagógicos que se citen en tu diálogo con el tutor.
        </p>
        <div class="pista-panel">
          <Icono nombre="candado" medida={13} />
          <span>Consulta libre sin evaluación</span>
        </div>
      </div>
    {/if}
  </div>

  <div class="pie-panel-der">
    <button
      type="button"
      class="ir-a-conceptos"
      onclick={() => navegar("/conceptos")}
    >
      <Icono nombre="conceptos" medida={16} />
      <span>Ver todos los conceptos</span>
    </button>
  </div>
</aside>



<Dialogo bind:abierto={fichaAbierta} titulo="Concepto" class="dialogo-concepto">
  {#if falloDeFicha}
    <Degradacion respuesta={falloDeFicha} alReintentar={null} />
  {:else if ficha}
    <FichaDeConcepto {ficha} alAbrir={abrirConcepto} />
  {/if}
</Dialogo>

<style>
  :global(dialog.dialogo-concepto:not([open])) {
    display: none !important;
  }

  :global(dialog.dialogo-concepto[open]) {
    max-inline-size: min(35rem, calc(100vw - 2rem));
    max-block-size: min(80vh, calc(100dvh - 4rem));
    padding: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin: auto;
  }

  :global(dialog.dialogo-concepto .cabecera-dialogo) {
    padding: 1.1rem 1.4rem;
    background: var(--surface-elevated);
    border-block-end: 1px solid var(--trazo-suave);
    margin-block-end: 0;
    flex-shrink: 0;
    z-index: 10;
  }

  :global(dialog.dialogo-concepto .cuerpo) {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 1.25rem 1.4rem;
    scrollbar-width: thin;
  }

  .abrir-panel-movil,
  .cerrar-panel-movil {
    display: none;
  }

  :global(.trabajo:has(.cabecera .mas[open])) .abrir-panel-movil,
  :global(.trabajo:has(.cabecera .menu-profesional)) .abrir-panel-movil {
    visibility: hidden;
    pointer-events: none;
  }

  .panel {
    inline-size: 20rem;
    min-inline-size: 18rem;
    max-inline-size: 24rem;
    flex-shrink: 0;
    min-block-size: 0;
    height: 100%;
    align-self: stretch;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    padding: 16px;
    background: var(--surface-panel);
    border-inline-start: 1px solid var(--trazo-suave);
    overflow: hidden;
  }

  .panel.oculto-escritorio {
    display: none;
  }

  .cabecera-panel-der {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-block-end: 14px;
    border-block-end: 1px solid var(--trazo-suave);
    margin-block-end: 14px;
    flex-shrink: 0;
  }

  .titular-panel {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--ink-primary);
  }

  .titular-panel h2 {
    margin: 0;
    font-size: var(--texto-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--ink-secondary);
  }

  .cuerpo-panel-der {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
  }

  .tarjeta-vacia-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 12px;
    padding: 24px 16px;
    background: var(--surface-paper);
    border: 1px dashed var(--trazo-suave);
    border-radius: var(--radius-md);
    box-sizing: border-box;
  }

  .icono-vacio {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--accent-surface);
    color: var(--accent-main);
  }

  .titulo-vacio-panel {
    margin: 0;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  .sin-conceptos {
    margin: 0;
    color: var(--ink-secondary);
    font-size: var(--texto-xs);
    line-height: 1.5;
  }

  .pista-panel {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--ink-tertiary);
    margin-block-start: 4px;
  }

  .pie-panel-der {
    margin-block-start: auto;
    padding-block-start: 14px;
    border-block-start: 1px solid var(--trazo-suave);
    flex-shrink: 0;
  }

  .ir-a-conceptos {
    inline-size: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5em;
    min-block-size: 42px;
    padding: 0.5em 1em;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    color: var(--ink-primary);
    font-size: var(--texto-xs);
    font-weight: 600;
    cursor: pointer;
    box-shadow: var(--shadow-soft);
    transition: var(--transition-fast);
  }

  .ir-a-conceptos:hover {
    color: var(--accent-main);
    border-color: var(--accent-main);
    background: var(--accent-surface);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px var(--accent-glow);
  }

  @media (max-width: 48rem) {
    .abrir-panel-movil {
      position: absolute;
      inset-block-start: 0.65rem;
      inset-inline-end: 0.75rem;
      z-index: 18;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      min-block-size: 44px;
      padding: 0.55rem 0.75rem;
      border: 1px solid var(--accent-main);
      border-radius: var(--radius-pill, 9999px);
      background: var(--surface-panel);
      color: var(--accent-main);
      box-shadow: var(--shadow-float);
      font: inherit;
      font-size: var(--texto-xs);
      font-weight: 700;
      cursor: pointer;
    }

    .abrir-panel-movil.oculto-al-escribir { display: none; }

    .panel {
      position: fixed;
      inset: 0;
      z-index: 60;
      display: flex;
      inline-size: 100%;
      min-inline-size: 0;
      max-inline-size: none;
      block-size: 100dvh;
      padding: var(--espacio-md);
      border: 0;
      transform: translateX(100%);
      visibility: hidden;
      transition: transform 0.22s ease-out, visibility 0.22s;
    }

    .panel.oculto-escritorio {
      display: flex;
    }

    .panel.abierto-movil {
      transform: none;
      visibility: visible;
    }

    .cerrar-panel-movil {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      inline-size: 44px;
      block-size: 44px;
      border: 1px solid var(--trazo-suave);
      border-radius: var(--radius-sm);
      background: var(--surface-paper);
      color: var(--ink-primary);
      cursor: pointer;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .panel { transition: none; }
  }
</style>
