<!--
«Material del curso»: lo que el turno recuperó, como controles accionables.

QUÉ AFIRMA ESTE RÓTULO, Y QUÉ NO
---------------------------------
Afirma **«esto se recuperó para este turno»**. No afirma que la respuesta lo
use, ni que una frase concreta se apoye en uno de estos fragmentos: el motor no
produce ese mapeo y el contrato lo dice con `relacion: 'recuperado'`.

Por eso el encabezado dice «Material consultado para esta respuesta» y no
«Fuentes que demuestran esta explicación». La segunda frase sería falsa hoy, y
lo seguiría siendo aunque quedara bonita. El día que exista trazabilidad por
afirmación, el contrato traerá otra `relacion` y este componente dirá otra cosa
— hasta entonces, no.

EL IDENTIFICADOR ES DATO SECUNDARIO
------------------------------------
El título que se lee es de la obra y su página. El `F-*` va debajo, en pequeño
y con su propio rótulo accesible: sirve para trazar y para reportar, no para
que alguien tenga que aprenderse un código para saber qué está leyendo.

SUSTITUYE AL TEXTO PLANO, NO AL AVISO
--------------------------------------
`AvisoDeProcedencia.svelte` sigue diciendo **si** hubo material o si el turno
operó sin fuente; eso es un estado del turno y no cambia. Lo que cambia es que
la lista de identificadores deja de ser una cadena y pasa a ser navegable.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import { tick } from 'svelte';
  import Icono from '../base/Icono.svelte';
  import { navegar } from '../../enrutado/navegar.js';
  import { caminoDeFuente } from '../../nucleo/fuentes/navegacion.js';

  let {
    /** Las piezas del contrato §7.bis: { id, obra, titulo, relacion }. */
    material = [],
    /** El camino al que volver desde la fuente. Se valida al usarlo. */
    volverA = undefined,
    /** El turno gobierna el botón; esta pieza gobierna la hoja modal. */
    abierto = $bindable(false)
  } = $props();

  const piezas = $derived(Array.isArray(material) ? material : []);
  let panel = $state();

  $effect(() => {
    if (!abierto) return;
    void tick().then(() => panel?.focus());
  });

  function abrir(id) {
    abierto = false;
    navegar(caminoDeFuente(id, volverA));
  }


  function cerrarConEscape(evento) {
    if (abierto && evento.key === 'Escape') abierto = false;
  }

  function cerrarFuera(evento) {
    if (abierto && panel && !panel.contains(evento.target)) abierto = false;
  }
</script>

<svelte:window onkeydown={cerrarConEscape} onpointerdown={cerrarFuera} />

{#if abierto && piezas.length}
  <div class="velo" role="presentation">
    <div
      class="material"
      role="dialog"
      aria-modal="true"
      aria-labelledby="material-{piezas[0].id}"
      tabindex="-1"
      bind:this={panel}
    >
      <header>
        <span class="marca"><Icono nombre="biblioteca" medida={18} /></span>
        <div>
          <p>TRAZABILIDAD DE LA RESPUESTA</p>
          <h4 id="material-{piezas[0].id}">Material consultado para esta respuesta</h4>
        </div>
        <button type="button" class="cerrar" aria-label="Cerrar material consultado"
                onclick={() => (abierto = false)}>
          <Icono nombre="cerrar" medida={17} />
        </button>
      </header>
      <p class="explicacion">
        Estos fragmentos fueron recuperados para preparar el turno. Puedes abrirlos y volver a la conversación sin perder tu recorrido.
      </p>
      <ul>
        {#each piezas as pieza, indice (pieza.id)}
          <li>
            <a
              href={caminoDeFuente(pieza.id, volverA)}
              onclick={(evento) => {
                /* Es un enlace de verdad —se puede copiar, abrir en otra pestaña
                   y usar con el teclado— y además navega sin recargar cuando se
                   pulsa normal. */
                if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.button) return;
                evento.preventDefault();
                abrir(pieza.id);
              }}
            >
              <span class="numero">{String(indice + 1).padStart(2, '0')}</span>
              <span class="contenido">
                <span class="titulo">{pieza.titulo || pieza.id}</span>
                <span class="rastro">
                  <span class="solo-lectores">Identificador del fragmento: </span>
                  {pieza.id}
                  {#if pieza.obra}<span class="obra"> · {pieza.obra}</span>{/if}
                </span>
              </span>
              <Icono nombre="flecha-der" medida={16} />
            </a>
          </li>
        {/each}
      </ul>
      <footer>
        <Icono nombre="escudo" medida={14} />
        <span>La lista indica recuperación documental; no sustituye la verificación de cada afirmación.</span>
      </footer>
    </div>
  </div>
{/if}

<style>
  /* El hilo y el panel de recursos son hermanos con capas propias. Mientras
     esta hoja está abierta, el hilo sube temporalmente para que la gráfica no
     atraviese visualmente el papel del diálogo. */
  :global(.hilo:has(.velo)) { z-index: 70; }
  /* En teléfono el acceso flotante al panel de conceptos es hermano del hilo.
     Ocultarlo mientras esta hoja está abierta garantiza que nunca tape la X
     ni intercepte su pulsación, aunque cambie el orden de capas del marco. */
  :global(.conversacion:has(.velo) .abrir-panel-movil) {
    visibility: hidden;
    pointer-events: none;
  }

  .velo {
    position: fixed;
    z-index: 95;
    /* `Turno` vive dentro del contenido, que forma una capa inferior a la
       cabecera global. La hoja empieza debajo de esa cabecera en vez de
       intentar taparla desde una capa hija y dejar el título oculto. */
    /* Se centra dentro del espacio realmente legible: entre la cabecera y el
       redactor flotante. Centrar contra todo el viewport lo hacía caer sobre
       la caja de escritura, especialmente en teléfonos. */
    inset: 3.45rem 0 9.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--espacio-md);
    background: color-mix(in srgb, var(--ink-primary) 18%, transparent);
    backdrop-filter: blur(3px);
    -webkit-backdrop-filter: blur(3px);
    animation: aparecer .2s ease-out both;
  }

  .material {
    display: flex;
    flex-direction: column;
    inline-size: min(30rem, 100%);
    max-block-size: min(42rem, calc(100% - 2 * var(--espacio-md)));
    padding: var(--espacio-lg);
    overflow: hidden;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-lg);
    /* La transparencia pertenece a los mensajes; una hoja de consulta debe
       separar con nitidez sus enlaces del gráfico que pueda haber debajo. */
    background: var(--surface-paper);
    box-shadow: var(--shadow-dialog);
    animation: deslizar .26s cubic-bezier(.22, 1, .36, 1) both;
  }

  header { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: .7rem; align-items: center; }
  header p { margin: 0 0 .15rem; color: var(--accent-main); font-size: 9px; font-weight: 800; letter-spacing: .08em; }
  .marca { display: grid; place-items: center; inline-size: 2.45rem; aspect-ratio: 1; border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); }
  h4 {
    margin: 0;
    font-size: var(--texto-md);
    font-weight: 750;
    color: var(--ink-primary);
  }
  .cerrar {
    display: grid;
    place-items: center;
    inline-size: 2.4rem;
    aspect-ratio: 1;
    border: 1px solid var(--trazo-suave);
    border-radius: 50%;
    background: var(--surface-paper);
    color: var(--ink-secondary);
    cursor: pointer;
  }
  .cerrar:hover { border-color: var(--accent-main); color: var(--accent-main); }
  .explicacion {
    margin: var(--espacio-md) 0;
    color: var(--ink-tertiary);
    font-size: var(--texto-sm);
    line-height: 1.55;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: .55rem;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  a {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: .65rem;
    padding: .75rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    background: var(--surface-paper);
    color: var(--ink-primary);
    text-decoration: none;
    /* En 360 px el título largo de una obra se parte en varias líneas en vez
       de empujar la burbuja del turno fuera del viewport. */
    overflow-wrap: anywhere;
    /* El objetivo táctil no baja de 44 px aunque el texto sea de una línea. */
    min-height: 58px;
  }

  a:hover {
    border-color: var(--accent-main);
    background: var(--accent-surface);
  }

  a:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  .titulo {
    font-size: var(--texto-sm);
    line-height: 1.35;
  }

  .contenido { display: grid; gap: .15rem; min-inline-size: 0; }
  .numero { color: var(--accent-main); font-family: var(--fuente-mono); font-size: var(--texto-xs); font-weight: 800; }

  .rastro {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    font-variant-numeric: tabular-nums;
  }

  .solo-lectores {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  footer { display: flex; gap: .45rem; align-items: flex-start; margin-block-start: var(--espacio-md); padding-block-start: var(--espacio-sm); border-block-start: 1px solid var(--trazo-suave); color: var(--ink-tertiary); font-size: 10px; line-height: 1.45; }
  footer :global(svg) { flex-shrink: 0; color: var(--accent-main); }

  @keyframes aparecer { from { opacity: 0; } }
  @keyframes deslizar { from { opacity: 0; transform: translateY(.75rem) scale(.985); } }

  @media (max-width: 36rem) {
    .velo { inset-block-end: 8.75rem; align-items: center; padding: .5rem; }
    .material { inline-size: 100%; max-block-size: min(82dvh, 42rem); padding: var(--espacio-md); border-end-start-radius: var(--radius-lg); border-end-end-radius: var(--radius-lg); }
    @keyframes deslizar { from { opacity: 0; transform: translateY(1.25rem); } }
  }

  @media (prefers-reduced-motion: reduce) {
    .velo, .material { animation: none; }
  }
</style>
