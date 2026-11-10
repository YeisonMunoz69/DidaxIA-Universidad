<!--
DD-13 · El concepto en detalle.

Explicación, relaciones con otros conceptos y su simulación. Es la pestaña
aparte que las docentes pidieron para no cargar la conversación.

Las relaciones que muestra son las mismas aristas del grafo pedagógico. Al
escribir «para entender esto hace falta antes aquello», las docentes dibujan
grafo sin necesidad de saber que existe un grafo.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  import EnlaceAConcepto from "./EnlaceAConcepto.svelte";
  import TextoDeConcepto from "./TextoDeConcepto.svelte";
  import Icono from "../base/Icono.svelte";

  let {
    /** { id, nombre, nodo, estado, concepcion, secciones, previos } */
    ficha,
    /** Se invoca con el identificador de un concepto previo o adyacente. */
    alAbrir = null,
    /** Concepto anterior en la lista: { id, nombre } | null */
    anterior = null,
    /** Concepto siguiente en la lista: { id, nombre } | null */
    siguiente = null,
  } = $props();

  const secciones = $derived(ficha?.secciones ?? []);
  const previos = $derived(ficha?.previos ?? []);
  const revisada = $derived(!/borrador|pendiente/i.test(ficha?.estado ?? ""));
</script>

<article class="ficha">
  <header class="cabecera-ficha">
    <div class="fila-superior">
      <h2>{ficha?.nombre ?? "Concepto"}</h2>
      {#if ficha?.estado}
        <span class="estado" class:sin-revisar={!revisada}>
          <span aria-hidden="true">{revisada ? "✓" : "◇"}</span>
          <span>{ficha.estado}</span>
        </span>
      {/if}
    </div>
  </header>

  <div class="cuerpo-secciones">
    {#if previos.length}
      <div class="franja-prerrequisitos">
        <div class="rotulo-prerrequisitos">
          <Icono nombre="ancla" medida={13} />
          <span>Prerrequisitos:</span>
        </div>
        <div class="lista-prerrequisitos">
          {#each previos as p (p.id)}
            <div class="item-prerrequisito">
              <EnlaceAConcepto
                concepto={{ id: p.id, nombre: p.nombre ?? 'Concepto relacionado' }}
                {alAbrir}
              />
              {#if p.motivo}
                <div class="motivo-prerrequisito">
                  <TextoDeConcepto texto={p.motivo} />
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#each secciones as s (s.titulo)}
      <section class="parte">
        <h3 class="titulo-seccion">{s.titulo}</h3>
        <div class="contenido-seccion">
          <TextoDeConcepto texto={s.texto} />
        </div>
      </section>
    {/each}

    {#if anterior || siguiente}
      <footer
        class="pie-navegacion-concepto"
        aria-label="Navegación secuencial de conceptos"
      >
        {#if anterior}
          <button
            type="button"
            class="btn-nav-concepto btn-anterior"
            onclick={() => alAbrir?.(anterior.id)}
          >
            <div class="icono-nav">
              <Icono nombre="flecha-izq" medida={14} />
            </div>
            <div class="detalles-nav">
              <span class="subtitulo-nav">Anterior</span>
              <span class="nombre-nav">{anterior.nombre}</span>
            </div>
          </button>
        {:else}
          <div class="espaciador-nav"></div>
        {/if}

        {#if siguiente}
          <button
            type="button"
            class="btn-nav-concepto btn-siguiente"
            onclick={() => alAbrir?.(siguiente.id)}
          >
            <div class="detalles-nav align-der">
              <span class="subtitulo-nav">Siguiente</span>
              <span class="nombre-nav">{siguiente.nombre}</span>
            </div>
            <div class="icono-nav">
              <Icono nombre="flecha-der" medida={14} />
            </div>
          </button>
        {/if}
      </footer>
    {/if}
  </div>
</article>

<style>
  .ficha {
    display: flex;
    flex-direction: column;
    inline-size: 100%;
    animation: entrarFicha 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes entrarFicha {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .cabecera-ficha {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
    padding: 0 0 0.85rem;
    border-block-end: 1px solid var(--trazo-suave);
    margin-block-end: 0.85rem;
  }

  .fila-superior {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
  }

  h2 {
    margin: 0;
    font-size: var(--texto-lg);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.25;
  }


  .estado {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 3px 9px;
    border-radius: var(--radius-xs);
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
    font-size: var(--texto-xs);
    font-weight: 600;
  }

  .sin-revisar {
    background: var(--surface-paper);
    color: var(--ink-secondary);
    border: 1px solid var(--trazo-suave);
  }

  .cuerpo-secciones {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: 0;
  }

  /* Prerrequisitos en franja compacta */
  .franja-prerrequisitos {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-soft);
  }

  .rotulo-prerrequisitos {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--accent-main);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .lista-prerrequisitos {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .item-prerrequisito {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px;
    font-size: var(--texto-xs);
  }

  .motivo-prerrequisito {
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    line-height: 1.4;
  }

  .motivo-prerrequisito :global(.texto) {
    margin: 0;
    font-size: var(--texto-xs);
    line-height: 1.4;
  }

  .parte {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
  }

  .titulo-seccion {
    margin: 0;
    font-size: var(--texto-sm);
    font-weight: 700;
    color: var(--ink-primary);
    letter-spacing: -0.01em;
  }

  .contenido-seccion {
    color: var(--ink-secondary);
    line-height: 1.6;
    font-size: var(--texto-base);
  }

  /* Navegación anterior / siguiente */
  .pie-navegacion-concepto {
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: var(--espacio-md);
    margin-block-start: var(--espacio-md);
    padding-block-start: var(--espacio-md);
    border-block-start: 1px solid var(--trazo-suave);
  }

  .espaciador-nav {
    flex: 1;
  }

  .btn-nav-concepto {
    flex: 1;
    max-inline-size: 48%;
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-soft);
    cursor: pointer;
    text-align: start;
    font: inherit;
    color: var(--ink-secondary);
    transition: var(--transition);
  }

  .btn-siguiente {
    justify-content: flex-end;
    text-align: end;
    margin-inline-start: auto;
  }

  .btn-nav-concepto:hover {
    border-color: var(--accent-main);
    background: var(--surface-canvas);
    color: var(--accent-main);
    transform: translateY(-1px);
    box-shadow: var(--shadow-card-hover);
  }

  .btn-anterior:hover {
    transform: translateX(-2px);
  }

  .btn-siguiente:hover {
    transform: translateX(2px);
  }

  .icono-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 28px;
    block-size: 28px;
    border-radius: var(--radius-xs);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    color: var(--accent-main);
    flex-shrink: 0;
    transition: var(--transition-fast);
  }

  .btn-nav-concepto:hover .icono-nav {
    background: var(--accent-surface);
    border-color: var(--accent-main);
  }

  .detalles-nav {
    display: flex;
    flex-direction: column;
    gap: 1px;
    overflow: hidden;
  }

  .align-der {
    align-items: flex-end;
  }

  .subtitulo-nav {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-tertiary);
  }

  .nombre-nav {
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .btn-nav-concepto:hover .nombre-nav {
    color: var(--accent-main);
  }
</style>
