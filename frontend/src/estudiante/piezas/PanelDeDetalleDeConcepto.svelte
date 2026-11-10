<!-- Panel derecho de la biblioteca: ficha seleccionada o invitación inicial. -->
<script>
  import DetalleDeConcepto from './DetalleDeConcepto.svelte';
  import { temaDeConcepto } from '../../nucleo/lectura/conceptos.js';
  import LibroInteractivo from '../../comun/lectura/LibroInteractivo.svelte';

  let {
    abierta = null,
    banco = [],
    cargando = false,
    anterior = null,
    siguiente = null,
    pagina = 1,
    total = 1,
    mostrarControles = true,
    alAbrir
  } = $props();
  const grupos = $derived([...new Set(banco.map(temaDeConcepto))].map(tema => ({
    tema, conceptos: banco.filter(concepto => temaDeConcepto(concepto) === tema)
  })));

</script>

<main class="panel-detalle">
  {#if abierta}

      <div class="tarjeta-ficha-contenedor">
        <LibroInteractivo
          titulo={`Libro de conceptos: ${abierta.nombre}`}
          mostrarCabecera={false}
          variante="conceptos"
          unaPagina
          identidad={abierta.id}
          {pagina}
          {total}
          {mostrarControles}
          anterior={anterior?.nombre}
          siguiente={siguiente?.nombre}
          alAnterior={() => anterior && alAbrir?.(anterior.id)}
          alSiguiente={() => siguiente && alAbrir?.(siguiente.id)}>
          {#snippet izquierda()}
            <DetalleDeConcepto ficha={abierta} {alAbrir} parte="portada" />
          {/snippet}
          {#snippet derecha()}
            <DetalleDeConcepto ficha={abierta} {alAbrir} parte="contenido" />
          {/snippet}
          {#snippet simple()}
            <DetalleDeConcepto ficha={abierta} {alAbrir} parte="completa" />
          {/snippet}
        </LibroInteractivo>
      </div>

  {:else if !cargando}
    <section class="catalogo-estudio" aria-label="Explorar el cuaderno por temas">
      <header><span class="etiqueta-estudio">Ideas · notación · conexiones</span><h2>Abre una idea y sigue sus conexiones</h2><p>Elige un tema para explorar las explicaciones del curso. Las marcas de consulta duran esta sesión y permanecen en tu navegador.</p></header>
      <div class="grupos-estudio">
        {#each grupos as grupo (grupo.tema)}
          <section class="grupo-estudio">
            <h3>{grupo.tema}<span>{grupo.conceptos.length} conceptos</span></h3>
            {#each grupo.conceptos.slice(0, 4) as concepto (concepto.id)}
              <button type="button" onclick={() => alAbrir?.(concepto.id)}><span>{concepto.nombre}</span><span aria-hidden="true">↗</span></button>
            {/each}
            {#if grupo.conceptos.length > 4}<p>Encuentra los demás en el índice.</p>{/if}
          </section>
        {/each}
      </div>
    </section>
  {/if}
</main>

<style>
  .panel-detalle {
    flex: 1;
    min-inline-size: 0;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    block-size: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--book-paper);
    border: 0;
    border-radius: 1rem;
    box-shadow: 0 14px 40px var(--book-cover-shadow);
  }

  .tarjeta-ficha-contenedor {
    flex: 1;
    min-block-size: 0;
    overflow: hidden;
    padding: 0;
    background: var(--book-paper);
    box-sizing: border-box;
    position: relative;
  }


  .catalogo-estudio { overflow-y: auto; padding: clamp(1.3rem,3vw,2.5rem); }
  .etiqueta-estudio { color: var(--accent-main); font: 700 .65rem/1.5 var(--fuente-mono); text-transform: uppercase; letter-spacing: .12em; }
  h2 { margin: .7rem 0; max-width: 24ch; font: 600 clamp(1.8rem,3vw,2.6rem)/1.12 Georgia,serif; color: var(--ink-primary); }
  .catalogo-estudio header p { max-width: 60ch; font-size: .9rem; line-height: 1.7; color: var(--ink-secondary); }
  .grupos-estudio { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,17rem),1fr)); gap: 1rem; margin-top: 1.7rem; }
  .grupo-estudio { padding: 1.2rem; border: 1px solid var(--trazo-suave); border-top: 3px solid var(--accent-main); border-radius: .8rem; background: color-mix(in srgb,var(--surface-paper) 40%,var(--book-paper)); }
  h3 { display: flex; align-items: baseline; justify-content: space-between; gap: .7rem; margin: 0 0 .8rem; font: 600 1.2rem/1.3 Georgia,serif; }
  h3 span,.grupo-estudio p { font: .7rem/1.5 var(--fuente-mono); color: var(--ink-tertiary); }
  .grupo-estudio button { display: flex; align-items: center; justify-content: space-between; gap: .8rem; width: 100%; min-height: 48px; padding: .65rem 0; text-align: left; border: 0; border-bottom: 1px solid var(--trazo-suave); background: transparent; color: var(--ink-secondary); font: inherit; font-size: .85rem; line-height: 1.5; cursor: pointer; }
  .grupo-estudio button:hover { color: var(--accent-main); }
  .grupo-estudio button:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }

  @media (max-width: 48rem) {
    .panel-detalle {
      border-radius: 0; box-shadow: none;
      max-block-size: none;
      flex: 1 1 auto;
      inline-size: 100%;
      max-inline-size: 100%;
    }

    .tarjeta-ficha-contenedor { padding: 0; }
  }
</style>
