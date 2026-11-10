
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import BloquesDeTexto from '../../comun/fuente/BloquesDeTexto.svelte';
  import LibroInteractivo from '../../comun/lectura/LibroInteractivo.svelte';
  import { navegar } from '../../enrutado/navegar.js';
  import { fragmento as pedirFragmento, esFragmento } from '../../nucleo/api/fuentes.js';
  import {
    PARAMETRO_DE_RETORNO,
    caminoDeObra,
    destinoDeRetorno,
    fragmentoDelCamino
  } from '../../nucleo/fuentes/navegacion.js';

  let {
    caminoActual = globalThis.location?.pathname ?? '',
    consultaActual = globalThis.location?.search ?? '',
    cargar = pedirFragmento
  } = $props();

  const identificador = $derived(fragmentoDelCamino(caminoActual));
  const volverA = $derived(
    destinoDeRetorno(new URLSearchParams(consultaActual).get(PARAMETRO_DE_RETORNO))
  );

  let estado = $state('cargando');
  let ficha = $state(null);
  let motivo = $state('');
  let explicacion = $state('');
  let modoLector = $state(true);

  const EXPLICACION = {
    fragmento_inexistente:
      'No hay material del curso con ese identificador. Puede que el enlace esté mal escrito.',
    recurso_no_catalogado: 'Este material todavía no está en el catálogo de la biblioteca.',
    obra_no_autorizada:
      'Esta obra todavía no tiene registrada la autorización necesaria para publicar su texto aquí. ' +
      'Su ficha bibliográfica sí se puede consultar.',
    recurso_retirado: 'Este material se retiró de la biblioteca.',
    archivo_ausente: 'El material no está disponible en este servidor.',
    pagina_sin_mapeo: 'No se puede señalar la página exacta de esta obra sin comprobarla antes.',
    recurso_no_servible: 'Este material no se puede abrir aquí.'
  };

  function explicar(clave, respaldo) {
    return EXPLICACION[clave] ?? respaldo ?? 'Este material no se puede abrir aquí.';
  }

  $effect(() => {
    const id = identificador;
    if (!id) {
      estado = 'no-encontrado';
      motivo = 'fragmento_inexistente';
      explicacion = EXPLICACION.fragmento_inexistente;
      return;
    }
    if (!esFragmento(id)) {
      estado = 'no-encontrado';
      motivo = 'fragmento_inexistente';
      explicacion = EXPLICACION.fragmento_inexistente;
      return;
    }

    const control = new AbortController();
    estado = 'cargando';
    ficha = null;
    motivo = '';
    cargar(id, { señal: control.signal })
      .then((datos) => {
        if (control.signal.aborted) return;
        ficha = datos;
        motivo = datos?.motivo_sin_contenido ?? '';
        explicacion = motivo ? explicar(motivo, datos?.explicacion_sin_contenido) : '';
        estado = 'listo';
      })
      .catch((fallo) => {
        if (control.signal.aborted) return;
        const clave = fallo?.cuerpo?.motivo ?? '';
        motivo = clave;
        explicacion = explicar(clave, fallo?.mensaje);
        estado = clave === 'obra_no_autorizada' ? 'no-autorizado' : 'no-encontrado';
      });
    return () => control.abort();
  });

  const obra = $derived(ficha?.obra ?? null);
  const procedencia = $derived(ficha?.procedencia ?? null);
  const localizacion = $derived(ficha?.localizacion ?? null);

  const pagina = $derived(
    !procedencia
      ? ''
      : procedencia.exacta
        ? `página ${procedencia.pagina}`
        : `páginas ${procedencia.pagina}–${procedencia.pagina_hasta}`
  );
  function abrirEnObra(vista) {
    navegar(caminoDeObra(obra.clave, {
      parte: localizacion?.parte?.split(':')?.[1], fragmento: ficha?.identificador, volverA, vista,
    }));
  }
</script>

{#snippet metadatos()}
  <header class="pagina-fuente metadatos-fuente">
    <p class="etiqueta">Material del curso · fragmento del corpus</p>
    <dl class="ficha">
      {#if obra}<div><dt>Obra</dt><dd>{obra.titulo}</dd></div>{/if}
      {#if pagina}
        <div>
          <dt>Procedencia</dt>
          <dd>{pagina}{#if procedencia && !procedencia.exacta}<span class="matiz"> · página aproximada dentro del rango</span>{/if}</dd>
        </div>
      {/if}
      <div><dt>Identificador</dt><dd><code>{ficha?.identificador ?? identificador}</code></dd></div>
      <div><dt>Verificación de su matemática</dt><dd>{ficha?.verificacion ?? 'sin marca'}</dd></div>
    </dl>
    <p class="naturaleza">
      Lo que sigue es <strong>texto de la obra</strong>, no una explicación generada por el asistente.
    </p>
  </header>
{/snippet}

{#snippet lectura()}
  <section class="pagina-fuente lectura-fuente" aria-labelledby="texto-del-fragmento">
    <p class="etiqueta">Pasaje citado · {ficha?.identificador ?? identificador}</p>
    <h1>{ficha?.titulo || identificador}</h1>
    <p class="procedencia-breve">{pagina}</p>
    <details class="procedencia-desplegable"><summary>Procedencia y verificación</summary>{@render metadatos()}</details>
    <h2 id="texto-del-fragmento">Texto del fragmento</h2>
    {#if ficha?.contenido}
      <BloquesDeTexto contenido={ficha.contenido} />
    {:else}
      <p class="aviso" role="status">{explicacion || EXPLICACION.recurso_no_servible}</p>
    {/if}
    {#if obra}
      <footer class="acciones">
        <Boton
          onclick={() => abrirEnObra()}>
          Ver en la obra
        </Boton>
        {#if localizacion}<Boton variante="discreto" onclick={() => abrirEnObra('original')}>Ver PDF original ↗</Boton>{/if}
        {#if localizacion === null}
          <p class="matiz">Todavía no se puede señalar en qué parte de la obra está este pasaje.</p>
        {/if}
      </footer>
    {/if}
  </section>
{/snippet}

{#snippet paginaMovil()}
  {@render lectura()}
{/snippet}

<article class="fuente" class:modo-lector={modoLector}>
  <nav class="volver" aria-label="Volver">
    <Boton variante="discreto" onclick={() => navegar(volverA)}>
      ← Volver a la conversación
    </Boton>
    <button type="button" class="modo" onclick={() => (modoLector = !modoLector)} aria-label={modoLector ? 'Salir del modo lector' : 'Leer sin distracciones'}>{modoLector ? '↙' : '⛶'}</button>
  </nav>

  {#if estado === 'cargando'}
    <h1>Material del curso</h1>
    <CargadorCubo mensaje="Buscando el material…" pantallaCompleta />
  {:else if estado === 'no-encontrado' || estado === 'no-autorizado'}
    <h1>Material del curso</h1>
    <p class="aviso" role="status">{explicacion}</p>
    {#if identificador}
      <p class="rastro">Identificador consultado: <code>{identificador}</code></p>
    {/if}
  {:else}
    <div class="libro-fuente">
      <LibroInteractivo titulo={`Fragmento ${ficha?.identificador ?? identificador}`} pagina={1} total={1} unaPagina mostrarCabecera={false} mostrarControles={false}>
        {#snippet izquierda()}{@render metadatos()}{/snippet}
        {#snippet derecha()}{@render lectura()}{/snippet}
        {#snippet simple()}{@render paginaMovil()}{/snippet}
      </LibroInteractivo>
    </div>
  {/if}
</article>

<style>
  .fuente.modo-lector { position: fixed; inset: 0; z-index: 120; width: 100%; max-width: none; height: 100dvh; padding: .25rem; background: var(--surface-canvas); }
  .fuente .volver { display: flex; justify-content: space-between; align-items: center; gap: .5rem; }
  .modo { min-width: 44px; min-height: 44px; border: 1px solid var(--trazo-suave); border-radius: 999px; color: var(--accent-main); background: var(--surface-paper); font-size: 1.2rem; cursor: pointer; }
  .procedencia-breve { color: var(--ink-secondary); font-size: .85rem; margin: -.5rem 0 1rem; }
  .procedencia-desplegable { padding-block: .6rem; border-block: 1px solid var(--trazo-suave); color: var(--ink-secondary); margin-bottom: 1rem; }
  .procedencia-desplegable summary { cursor: pointer; min-height: 32px; }
  .procedencia-desplegable .metadatos-fuente { min-height: 0; padding: .5rem 0; }
  .lectura-fuente :global(.texto-del-corpus) { font-family: Georgia,serif; font-size: clamp(1rem,1.2vw,1.12rem); line-height: 1.75; }
  .fuente h2 { margin-block: 1rem .7rem; }
  .modo-lector :global(.mesa) { padding: 0; border-radius: 0; }
  .fuente {
    width: 100%;
    max-width: 82rem;
    margin: 0 auto;
    padding: var(--espacio-sm) var(--espacio-md) var(--espacio-md);
    min-width: 0;
    block-size: 100%;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
  }

  .volver {
    margin-bottom: var(--espacio-xs);
    flex: 0 0 auto;
  }

  .libro-fuente { flex: 1; min-block-size: 0; }

  .pagina-fuente {
    padding: clamp(1.1rem, 3vw, 2.2rem);
    box-sizing: border-box;
  }

  .metadatos-fuente {
    min-block-size: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .lectura-fuente { min-block-size: 100%; }

  .etiqueta {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  h1 {
    margin: var(--espacio-xs) 0 var(--espacio-md);
    font-size: 1.4rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }

  h2 {
    font-size: 1.05rem;
    margin: var(--espacio-xl) 0 var(--espacio-sm);
  }

  .ficha {
    display: grid;
    gap: var(--espacio-sm);
    margin: 0 0 var(--espacio-lg);
    padding: var(--espacio-md);
    background: var(--surface-panel);
    border-radius: var(--radius-md);
  }

  .ficha div {
    display: grid;
    grid-template-columns: minmax(9rem, 12rem) 1fr;
    gap: var(--espacio-sm);
  }

  @media (max-width: 32rem) {
    .ficha div {
      grid-template-columns: 1fr;
      gap: 0;
    }
  }

  dt {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  dd {
    margin: 0;
    font-size: var(--texto-sm);
    overflow-wrap: anywhere;
  }

  .naturaleza {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    border-inline-start: 3px solid var(--accent-main);
    padding-inline-start: var(--espacio-sm);
    margin: 0 0 var(--espacio-md);
  }

  .aviso {
    font-size: var(--texto-sm);
    color: var(--semantic-warning);
    background: var(--semantic-warning-bg);
    padding: var(--espacio-md);
    border-radius: var(--radius-sm);
  }

  .matiz {
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .rastro {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .acciones {
    margin-top: var(--espacio-xl);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--espacio-sm);
  }

  @media (max-width: 48rem) {
    .fuente { padding: var(--espacio-xs); }
    .pagina-fuente { padding: 1.15rem; }
    .metadatos-fuente { min-block-size: auto; justify-content: flex-start; }
  }
</style>
