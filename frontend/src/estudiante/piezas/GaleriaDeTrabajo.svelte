<!--
La galería de trabajo · gráficas y fórmulas de TODA la conversación.

Del mockup —`.tool-section`/`.graph-wrapper`/`.legend`—, con una diferencia
que el propio mockup no tenía que resolver: ahí solo existía LA gráfica del
turno actual, una sola tarjeta fija en el panel. Aquí una conversación puede
traer varias —el pedido fue verlas todas según van apareciendo, no solo la
última—, así que esto es una lista que crece con el hilo.

SE DERIVA DE LO QUE YA SE ESTÁ MOSTRANDO, NO SE ACUMULA APARTE
------------------------------------------------------------------
Quien monta esta pieza pasa el hilo que Conversacion.svelte ya calculó
—`hiloAMostrar`: en vivo o una conversación pasada, según el carril—, y
aquí solo se recorre con `$derived`. Ese hilo ya trae todos los bloques de
todos los turnos, así que no hace falta un segundo `$state` que acumule por
su cuenta y se pueda desincronizar. Es distinto de `conceptos`, en
`Conversacion.svelte`: ese SÍ es un acumulador propio, porque `conceptos`
es un campo de nivel de turno que no vive dentro de `bloques`.

CRONOLÓGICA, EN EL ORDEN DEL HILO. No es «lo último arriba»: es un
recorrido de la conversación, y el orden en que las cosas se dijeron es
parte de lo que se está consultando.

CADA GRÁFICA SE REMONTA CON SU PROPIO TABLERO. `Grafica.svelte` ya lo
soporta —cada instancia inicializa y libera su propio tablero JSXGraph al
montarse y desmontarse—, así que una lista de varias no es distinta de
pintar una sola vez por vez: es la misma pieza, repetida.



-->
<script>
  import { tick } from 'svelte';
  import Grafica from '../../comun/turno/Grafica.svelte';
  import Graficadora from '../../comun/rutas/Graficadora.svelte';
  import Notacion from '../../comun/turno/Notacion.svelte';
  import Prosa from '../../comun/turno/Prosa.svelte';
  import ReportarProblema from '../../comun/rutas/ReportarProblema.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { identificadorDeGrafica } from '../../nucleo/api/telemetria.js';
  import {
    agruparItemsDeGaleria,
    formulasDeGrafica,
    itemsDeGaleria,
    traeDerivada
  } from '../../nucleo/presentacion/materialDelHilo.js';

  let {
    /** El hilo que se está mostrando —en vivo o una conversación pasada—,
        con la forma `{ autor, turno }` del contrato §4.2. */
    hilo = [],
    solicitudGrafica = null,
    alCerrarDesdeChat = null,
    soloLectura = false
  } = $props();

  const items = $derived(itemsDeGaleria(hilo));

  /**
   * `items`, agrupado por turno.
   *
   * No hay todavía un identificador de ejercicio en el contrato —un mismo
   * problema puede seguir en el turno siguiente y esto no lo sabría—, así
   * que el turno es la aproximación disponible hoy: lo que se dijo en el
   * mismo intercambio suele ser del mismo paso. `Map` conserva el orden de
   * inserción, que ya es cronológico porque `items` lo es.
   */
  const grupos = $derived(agruparItemsDeGaleria(items));

  /**
   * Con una sola gráfica, la tarjeta completa —tablero a 135px y leyenda—
   * es del tamaño que le corresponde a lo único que hay que mostrar. Con
   * varias, esa misma tarjeta repetida es una lista larga de desplazar
   * para ver una fila de curvas; a partir de la segunda, cada una se
   * reduce a una miniatura del tamaño de un botón con su título al lado.
   */
  const graficas = $derived(items.filter((item) => item.tipo === 'grafica'));
  const hayVariasGraficas = $derived(graficas.length > 1);
  let seleccionada = $state(null);
  let disparadorActivo = null;
  let dialogo = $state(null);
  let botonCerrar = $state(null);
  let abiertaDesdeChat = false;
  let solicitudProcesada = null;

  $effect(() => {
    if (!solicitudGrafica || solicitudGrafica === solicitudProcesada) return;
    const item = items.find((candidato) => candidato.tipo === 'grafica'
      && candidato.contenido === solicitudGrafica.definicion
      && candidato.turno === solicitudGrafica.turno);
    if (item) {
      solicitudProcesada = solicitudGrafica;
      void abrirGrafica(item, solicitudGrafica.disparador, true);
    }
  });

  function numeroDeGrafica(item) {
    return graficas.findIndex((grafica) => grafica.clave === item?.clave) + 1;
  }

  function descripcionVisibleDeGrafica(alternativo) {
    const texto = alternativo || 'Gráfica matemática';
    // El texto alternativo completo sigue disponible para lectores de pantalla.
    // En la tarjeta la fórmula ya se pinta con Notacion; repetir la versión
    // ASCII del servidor produce una segunda expresión sin formato.
    if (texto.includes('$') || !/\b[fg]\([a-zA-Z]\)\s*=/.test(texto)) return texto;
    const cerca = texto.match(/\bcerca de\s+[^.]+/i)?.[0];
    if (cerca) return `Gráfica de la función ${cerca}`;
    if (/\by su derivada\b/i.test(texto)) return 'Gráfica de la función y su derivada';
    if (/\b(?:y su tangente|tangente de)\b/i.test(texto)) return 'Gráfica y tangente de la función';
    if (/\by g\([a-zA-Z]\)\s*=/.test(texto)) return 'Gráficas de las funciones';
    return 'Gráfica de la función';
  }

  function contextoDeGrafica(item) {
    const identificador = identificadorDeGrafica(item?.contenido);
    return [
      'Origen: tarjeta de gráfica en la galería de trabajo.',
      identificador ? `Gráfica: ${identificador}` : '',
      sesion.conversacion ? `Conversación: ${sesion.conversacion}` : '',
      item?.turno ? `Turno: ${item.turno}` : '',
      item?.clase ? `Clase: ${item.clase}` : '',
      item?.concepto ? `Concepto: ${item.concepto}` : ''
    ].filter(Boolean).join('\n');
  }

  async function abrirGrafica(item, disparador, desdeChat = false) {
    disparadorActivo = disparador;
    abiertaDesdeChat = desdeChat;
    seleccionada = item;
    await tick();
    botonCerrar?.focus();
  }

  async function cerrarGrafica() {
    if (!seleccionada) return;
    seleccionada = null;
    await tick();
    if (abiertaDesdeChat) alCerrarDesdeChat?.();
    abiertaDesdeChat = false;
    disparadorActivo?.focus();
  }

  function manejarTeclado(evento) {
    if (!seleccionada) return;
    // Marca el evento antes de que otros contenedores del shell lo reciban.
    // El DOM del diálogo puede desaparecer durante el mismo despacho.
    evento.didaxiaDialogo = true;
    if (evento.key === 'Escape') {
      // La gráfica tiene su propia vista de pantalla completa. El primer
      // Escape sale de ella; un segundo Escape cierra esta selección.
      if (dialogo?.querySelector('.pantalla-completa')) return;
      evento.preventDefault();
      evento.stopImmediatePropagation();
      void cerrarGrafica();
      return;
    }
    if (evento.key !== 'Tab' || !dialogo) return;
    const enfocables = [...dialogo.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )];
    if (!enfocables.length) return;
    const primero = enfocables[0];
    const ultimo = enfocables.at(-1);
    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }
</script>

<svelte:window onkeydowncapture={manejarTeclado} />

{#if items.length}
  <section class="galeria" aria-labelledby="galeria-titulo">
    <h2 id="galeria-titulo">Gráficas y fórmulas</h2>
    <div class="grupos">
      {#each grupos as grupo (grupo.indiceDeTurno)}
        <ul class="grupo-turno">
          {#each grupo.items as item (item.clave)}
            {#if item.tipo === 'grafica' && hayVariasGraficas}
              <li class="tarjeta selector-grafica">
                <button
                  type="button"
                  class="boton-grafica"
                  aria-haspopup="dialog"
                  aria-label={`Abrir gráfica ${numeroDeGrafica(item)}: ${item.alternativo || 'Gráfica matemática'}`}
                  onclick={(evento) => abrirGrafica(item, evento.currentTarget)}
                >
                  <span class="numero-grafica">Gráfica {numeroDeGrafica(item)}</span>
                  <span class="titulo-grafica"><Prosa contenido={descripcionVisibleDeGrafica(item.alternativo)} enLinea /></span>
                  {#each formulasDeGrafica(item.contenido) as formula}
                    <span class="formula-grafica"><Notacion expresion={formula} compacto agrandar /></span>
                  {/each}
                  <span class="accion-grafica">Ver y explorar</span>
                </button>
                <div class="acciones-selector">
                  {#if !soloLectura}<ReportarProblema
                    compacto
                    presentacion="previa"
                    etiqueta="Reportar error"
                    etiquetaAria={`Reportar un error en la gráfica ${numeroDeGrafica(item)}`}
                    categoriaInicial="visual"
                    tituloInicial="Error en una gráfica matemática"
                    contexto={contextoDeGrafica(item)}
                  />{/if}
                </div>
              </li>
            {:else}
              <li class="tarjeta">
                {#if item.tipo === 'grafica'}
                  <div class="cabecera-tarjeta-grafica">
                    <span>Gráfica {numeroDeGrafica(item)}</span>
                    {#if !soloLectura}<ReportarProblema
                      compacto
                      presentacion="previa"
                      etiqueta="Reportar error"
                      etiquetaAria="Reportar un error en la gráfica 1"
                      categoriaInicial="visual"
                      tituloInicial="Error en una gráfica matemática"
                      contexto={contextoDeGrafica(item)}
                    />{/if}
                  </div>
                  <Grafica definicion={item.contenido} alternativo={item.alternativo} {soloLectura}
                           clase={item.clase} conversacion={sesion.conversacion}
                           turno={item.turno} concepto={item.concepto} compacto />
                  <!-- Mismos dos colores que ya traza `Grafica.svelte` por dentro
                       —`--color-violet-light`/`--color-amber-chart`—: la leyenda
                       solo los nombra, no elige ninguno nuevo. -->
                  <div class="leyenda">
                    <span class="leyenda-item">
                      <span class="linea funcion" aria-hidden="true"></span> f(x)
                    </span>
                    {#if traeDerivada(item.contenido)}
                      <span class="leyenda-item">
                        <span class="linea derivada" aria-hidden="true"></span> f′(x)
                      </span>
                    {/if}
                  </div>
                {:else}
                  <Notacion expresion={item.contenido ?? ''} alternativo={item.alternativo} bloque compacto />
                {/if}
              </li>
            {/if}
          {/each}
        </ul>
      {/each}
    </div>
  </section>
{/if}

{#if seleccionada}
  <div
    class="capa-dialogo"
    role="presentation"
    onpointerdown={(evento) => evento.target === evento.currentTarget && cerrarGrafica()}
  >
    <div
      class="dialogo-grafica"
      role="dialog"
      aria-modal="true"
      aria-labelledby="grafica-seleccionada-titulo"
      bind:this={dialogo}
    >
      <header class="cabecera-dialogo">
        <div>
          <p>Gráfica del hilo</p>
          <h3 id="grafica-seleccionada-titulo">Gráfica {numeroDeGrafica(seleccionada)}</h3>
        </div>
        <button
          type="button"
          class="cerrar-dialogo"
          aria-label="Cerrar gráfica seleccionada"
          onclick={cerrarGrafica}
          bind:this={botonCerrar}
        >Cerrar</button>
      </header>
      <p class="descripcion-grafica"><Prosa contenido={descripcionVisibleDeGrafica(seleccionada?.alternativo)} enLinea /></p>
      {#each formulasDeGrafica(seleccionada?.contenido) as formula}
        <div class="formula-dialogo"><Notacion expresion={formula} compacto agrandar /></div>
      {/each}
      {#key seleccionada?.clave}{#if soloLectura}<Grafica definicion={seleccionada?.contenido} alternativo={seleccionada?.alternativo} soloLectura />{:else}<Graficadora
        definicionInicial={seleccionada?.contenido}
        alternativo={seleccionada?.alternativo}
        integrada
        clase={seleccionada?.clase}
        conversacion={sesion.conversacion}
        turno={seleccionada?.turno}
        concepto={seleccionada?.concepto}
      />{/if}{/key}
      <div class="leyenda leyenda-dialogo">
        <span class="leyenda-item"><span class="linea funcion" aria-hidden="true"></span> f(x)</span>
        {#if traeDerivada(seleccionada?.contenido)}
          <span class="leyenda-item"><span class="linea derivada" aria-hidden="true"></span> f′(x)</span>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  /* Mismo lenguaje de rótulo que ya usa `PanelDeConceptos`, la otra sección
     de este panel: mayúsculas pequeñas, terciario, tracking suelto. No se
     comparte la regla —Svelte no tiene mixins entre componentes—, se repite
     a propósito para que las dos secciones lean como parte del mismo panel. */
  h2 {
    margin: 0 0 0.4rem;
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .galeria {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .grupos {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* Un turno puede traer varias tarjetas —gráfica y su fórmula, por
     ejemplo—; ESAS van juntas y sin línea entre ellas. La línea marca el
     salto a otro intercambio, no cada tarjeta. */
  .grupo-turno {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .grupo-turno:not(:first-child) {
    padding-block-start: 10px;
    border-block-start: 1px solid var(--trazo-suave);
  }

  .tarjeta {
    padding: 6px 8px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-soft);
    transition: var(--transition-fast);
  }

  .tarjeta:hover { box-shadow: var(--shadow-card-hover); }

  .tarjeta.selector-grafica {
    padding: 0;
  }

  .boton-grafica {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 3px 10px;
    inline-size: 100%;
    min-block-size: 52px;
    padding: 9px 10px;
    border: 0;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    background: transparent;
    color: var(--ink-primary);
    text-align: start;
    cursor: pointer;
    touch-action: manipulation;
  }

  .boton-grafica:hover { background: var(--accent-surface); }
  .boton-grafica:focus-visible {
    outline: 3px solid var(--accent-main);
    outline-offset: 2px;
  }

  .acciones-selector {
    display: flex;
    justify-content: flex-end;
    padding: 3px 6px;
    border-block-start: 1px solid var(--trazo-suave);
  }

  .cabecera-tarjeta-grafica {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .5rem;
    margin-block-end: 4px;
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 700;
  }

  .numero-grafica {
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--accent-main);
  }

  .titulo-grafica {
    grid-column: 1;
    min-inline-size: 0;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    overflow-wrap: anywhere;
  }
  .formula-grafica { grid-column: 1; min-inline-size: 0; overflow-x: auto; font-size: var(--texto-xs); }
  .formula-dialogo { max-inline-size: 100%; margin-block: .25rem; overflow-x: auto; }

  .accion-grafica {
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: center;
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--accent-main);
  }

  .leyenda {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-block-start: 0.3rem;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
  }

  .leyenda-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  /*
    `background`, Y NO `border`, ES LO QUE HACE ESTO SEGURO DE MEDIR.

    `--color-violet-light`/`--color-amber-chart` están anotados en
    `tokens.css` como «solo gráfico» — pensados para el trazo de una curva
    en el tablero, no para el cromado de la interfaz, y por eso
    `contraste.prueba.js` los mide contra las tres superficies en cuanto
    aparecen como color de PRIMER PLANO (`border`, `color`, `outline`…) sin
    fondo propio en la misma regla. `--color-amber-chart` da 1.85 contra
    `--surface-canvas` — bien para una curva sobre el papel del tablero, mal
    para lo que ese comprobador exige a un borde. Como `background` cuenta
    como FONDO y no como primer plano, esta pastilla no entra en esa
    medición: es tinta plana, no un borde que delimite nada.
  */
  .linea {
    inline-size: 0.9rem;
    block-size: 0.35rem;
    border-radius: 1px;
  }

  .funcion { background: var(--color-violet-light); }

  .derivada { background: var(--color-amber-chart); }

  .capa-dialogo {
    position: fixed;
    z-index: 70;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 16px;
    background: var(--velo-modal);
  }

  .dialogo-grafica {
    inline-size: min(920px, 100%);
    max-block-size: calc(100dvh - 32px);
    overflow: auto;
    padding: 16px;
    border: 1px solid var(--trazo-fuerte);
    border-radius: var(--radius-lg);
    background: var(--surface-panel);
    box-shadow: var(--shadow-float);
  }

  .cabecera-dialogo {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-block-end: 8px;
  }

  .cabecera-dialogo p,
  .cabecera-dialogo h3,
  .descripcion-grafica { margin: 0; }
  .cabecera-dialogo p { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .cabecera-dialogo h3 { color: var(--ink-primary); font-size: var(--texto-lg); }
  .descripcion-grafica { margin-block-end: 8px; color: var(--ink-secondary); }

  .cerrar-dialogo {
    min-inline-size: 72px;
    min-block-size: 44px;
    padding: 8px 12px;
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-sm);
    background: var(--surface-paper);
    color: var(--accent-main);
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .cerrar-dialogo:hover { background: var(--accent-surface); }
  .cerrar-dialogo:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 2px; }
  .leyenda-dialogo { margin-block-start: 8px; }

  @media (max-width: 32rem) {
    .capa-dialogo { padding: 4px; }
    .dialogo-grafica {
      max-block-size: calc(100dvh - 8px);
      padding: 10px;
      border-radius: var(--radius-sm);
    }
    .accion-grafica { grid-column: 1; grid-row: auto; }
  }

  @media (prefers-reduced-motion: reduce) {
    .tarjeta { transition: none; }
  }
</style>
