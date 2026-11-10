<!-- Biblioteca navegable del corpus: obras por nombre y partes catalogadas. -->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import * as api from '../../nucleo/api/fuentes.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { navegar } from '../../enrutado/navegar.js';

  let obras = $state([]);
  let fragmentos = $state([]);
  let seleccionada = $state(null);
  let ficha = $state(null);
  let cargando = $state(true);
  let cargandoFicha = $state(false);
  let fallo = $state(null);
  let falloFragmentos = $state(null);
  let consulta = $state('');
  let peticionFicha = 0;

  const normalizar = (valor) => String(valor ?? '')
    .normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es');
  const visibles = $derived(obras.filter((obra) =>
    normalizar(`${obra.titulo} ${obra.autoria}`).includes(normalizar(consulta))
  ));
  const fragmentosDeObra = $derived(fragmentos.filter((fragmento) =>
    fragmento.obra === seleccionada
  ));

  async function cargar() {
    cargando = true;
    fallo = null;
    try {
      // Las obras y sus partes son el núcleo de la biblioteca. El índice de
      // pasajes es complementario: si un backend anterior todavía no expone
      // esa colección, no debe vaciar también el catálogo que sí pudo leer.
      obras = await api.obras();
      await cargarFragmentos();
      if (!seleccionada && obras.length && !globalThis.matchMedia?.('(max-width: 47.999rem)').matches) await elegir(obras[0].clave);
    } catch (error) {
      fallo = describir(error);
    } finally {
      cargando = false;
    }
  }

  async function cargarFragmentos() {
    falloFragmentos = null;
    try {
      fragmentos = await api.fragmentos();
    } catch (error) {
      fragmentos = [];
      falloFragmentos = describir(error);
    }
  }

  async function elegir(clave) {
    const actual = ++peticionFicha;
    seleccionada = clave;
    ficha = null;
    cargandoFicha = true;
    try {
      const datos = await api.obra(clave);
      if (actual === peticionFicha) ficha = datos;
    } catch (error) {
      if (actual !== peticionFicha) return;
      fallo = describir(error);
    } finally {
      if (actual === peticionFicha) cargandoFicha = false;
    }
  }

  function abrirObra(clave, parte = '') {
    const parametros = new URLSearchParams({ volver: '/biblioteca' });
    if (parte) parametros.set('parte', parte);
    navegar(`/obras/${clave}?${parametros.toString()}`);
  }


  function abrirFragmento(identificador) {
    navegar(`/fuentes/${identificador}?volver=%2Fbiblioteca`);
  }

  $effect(() => { cargar(); });
</script>

<section class="biblioteca">
  <header class="cabecera-biblioteca">
    <div>
      <span class="ceja">Material institucional</span>
      <h1>Biblioteca del curso</h1>
      <p>Explora los libros y abre sus fragmentos transcritos o el ejemplar en PDF.</p>
    </div>
    <span class="privada"><Icono nombre="candado" medida={13} /> Consulta institucional</span>
  </header>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  <div class="estanteria" class:con-seleccion={Boolean(seleccionada)}>
    <aside class="catalogo" aria-label="Obras del curso">
      <label class="buscador">
        <Icono nombre="buscar" medida={15} />
        <span class="solo-lectura-asistida">Buscar una obra</span>
        <input type="search" bind:value={consulta} placeholder="Buscar por título o autor" />
      </label>

      {#if cargando}
        <CargadorCubo mensaje="Ordenando la biblioteca…" pantallaCompleta />
      {:else if visibles.length}
        <ul>
          {#each visibles as obra (obra.clave)}
            <li>
              <button type="button" class:activa={seleccionada === obra.clave}
                aria-current={seleccionada === obra.clave ? 'true' : undefined}
                onclick={() => elegir(obra.clave)}>
                <span class="mini-cubierta" aria-hidden="true">{obra.titulo?.trim()?.[0] || 'L'}</span>
                <span class="datos-obra">
                  <strong>{obra.titulo}</strong>
                  <span>{obra.autoria || 'Autoría catalogada en la ficha'}</span>
                </span>
                <span aria-hidden="true">›</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="estado">No hay obras que coincidan con la búsqueda.</p>
      {/if}
    </aside>

    <main class="detalle-biblioteca" aria-live="polite">
      {#if seleccionada}<button type="button" class="volver-catalogo" onclick={() => { peticionFicha++; seleccionada = null; ficha = null; cargandoFicha = false; }}>← Volver al catálogo</button>{/if}
      {#if cargandoFicha}
        <CargadorCubo mensaje="Abriendo la ficha…" pantallaCompleta />
      {:else if ficha}
        <div class="presentacion-obra">
          <div class="cubierta-grande" aria-hidden="true">
            <span>{ficha.titulo?.trim()?.[0] || 'L'}</span>
            <i></i>
          </div>
          <div class="metadatos">
            <span class="ceja">Obra del curso</span>
            <h2>{ficha.titulo}</h2>
            <p>{ficha.autoria}</p>
            <button type="button" class="abrir-principal" onclick={() => abrirObra(ficha.clave)}>
              <Icono nombre="biblioteca" medida={16} />
              <span>Abrir libro</span>
            </button>
          </div>
        </div>

        <section class="partes" aria-labelledby="titulo-partes">
          <div class="cabecera-partes">
            <div>
              <span class="ceja">Lectura por partes</span>
              <h3 id="titulo-partes">Fragmentos y capítulos disponibles</h3>
            </div>
            <span>{ficha.partes?.length ?? 0}</span>
          </div>
          {#if ficha.partes?.length}
            <ol>
              {#each ficha.partes as parte, indice (parte.identificador)}
                <li>
                  <button type="button" onclick={() => abrirObra(ficha.clave, parte.nombre)}>
                    <span class="numero">{String(indice + 1).padStart(2, '0')}</span>
                    <span class="datos-parte">
                      <strong>{parte.titulo || `Parte ${indice + 1}`}</strong>
                      <span>Páginas {parte.pagina_impresa_inicial}–{parte.pagina_impresa_final}</span>
                    </span>
                    <Icono nombre="flecha-der" medida={15} />
                  </button>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="estado">Esta obra no tiene partes transcritas catalogadas todavía.</p>
          {/if}
        </section>

        <section class="partes fragmentos" aria-labelledby="titulo-fragmentos">
          <div class="cabecera-partes">
            <div>
              <span class="ceja">Pasajes del tutor</span>
              <h3 id="titulo-fragmentos">Fragmentos de esta obra</h3>
            </div>
            <span>{fragmentosDeObra.length}</span>
          </div>
          {#if falloFragmentos}
            <div class="aviso-fragmentos" role="status">
              <span>Los libros están disponibles, pero no se pudo cargar el índice de pasajes.</span>
              <button type="button" onclick={cargarFragmentos}>Reintentar pasajes</button>
            </div>
          {:else if fragmentosDeObra.length}
            <ol>
              {#each fragmentosDeObra as fragmento (fragmento.identificador)}
                <li>
                  <button type="button" onclick={() => abrirFragmento(fragmento.identificador)}>
                    <span class="numero">{fragmento.identificador}</span>
                    <span class="datos-parte">
                      <strong>{fragmento.titulo}</strong>
                      <span>Página {fragmento.pagina}{fragmento.pagina_hasta && fragmento.pagina_hasta !== fragmento.pagina ? `–${fragmento.pagina_hasta}` : ''}</span>
                    </span>
                    <Icono nombre="flecha-der" medida={15} />
                  </button>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="estado">No hay fragmentos independientes catalogados para esta obra.</p>
          {/if}
        </section>
      {:else if !cargando}
        <div class="vacia">
          <Icono nombre="biblioteca" medida={34} />
          <h2>Elige un libro</h2>
          <p>Su ficha y sus lecturas disponibles aparecerán aquí.</p>
        </div>
      {/if}
    </main>
  </div>
</section>

<style>
  .volver-catalogo { display: none; min-height: 44px; padding: .6rem .75rem; margin-bottom: .7rem; background: var(--surface-paper); border: 1px solid var(--trazo-suave); border-radius: 999px; color: var(--accent-main); font: inherit; cursor: pointer; }
  .biblioteca {
    flex: 1;
    min-block-size: 0;
    inline-size: min(100%, 86rem);
    margin-inline: auto;
    padding: var(--espacio-md) var(--espacio-lg) var(--espacio-lg);
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    overflow: hidden;
    box-sizing: border-box;
  }

  .cabecera-biblioteca {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-shrink: 0;
  }
  .cabecera-biblioteca h1 { margin: .08rem 0 .2rem; color: var(--ink-primary); font-size: var(--texto-xl); }
  .cabecera-biblioteca p { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .ceja { color: var(--accent-main); font-size: .68rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
  .privada { display: inline-flex; align-items: center; gap: .35rem; padding: .35rem .65rem; border: 1px solid var(--trazo-suave); border-radius: 999px; color: var(--ink-secondary); font-size: var(--texto-xs); white-space: nowrap; }

  .estanteria { flex: 1; min-block-size: 0; display: grid; grid-template-columns: minmax(17rem, 22rem) minmax(0, 1fr); gap: var(--espacio-md); overflow: hidden; }
  .catalogo, .detalle-biblioteca { min-block-size: 0; border: 1px solid var(--trazo-suave); border-radius: var(--radius-lg, 18px); background: var(--surface-panel); box-shadow: var(--shadow-soft); }
  .catalogo { padding: .8rem; overflow-y: auto; scrollbar-width: thin; }
  .buscador { position: sticky; z-index: 2; inset-block-start: 0; display: flex; align-items: center; gap: .45rem; padding: .65rem .75rem; margin-block-end: .7rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-tertiary); }
  .buscador input { flex: 1; min-inline-size: 0; border: 0; outline: 0; background: transparent; color: var(--ink-primary); font: inherit; font-size: var(--texto-sm); }
  .catalogo ul, .partes ol { margin: 0; padding: 0; list-style: none; display: grid; gap: .5rem; }
  .catalogo button { inline-size: 100%; display: grid; grid-template-columns: 44px minmax(0,1fr) auto; align-items: center; gap: .7rem; padding: .6rem; border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; color: var(--ink-secondary); font: inherit; text-align: start; cursor: pointer; transition: transform .2s ease, background .2s ease, border-color .2s ease; }
  .catalogo button:hover { transform: translateX(2px); background: var(--surface-canvas); }
  .catalogo button.activa { border-color: var(--accent-main); background: var(--accent-surface); color: var(--accent-main); }
  .mini-cubierta { display: grid; place-items: center; inline-size: 42px; block-size: 54px; border-radius: 3px 7px 7px 3px; background: linear-gradient(145deg, var(--book-cover-start), var(--book-cover-end)); color: var(--book-cover-ink); font: 700 1rem/1 ui-serif, Georgia, serif; box-shadow: inset 4px 0 var(--book-cover-thread), 0 5px 10px var(--book-cover-shadow); }
  .datos-obra { min-inline-size: 0; display: flex; flex-direction: column; gap: .18rem; }
  .datos-obra strong, .datos-obra span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .datos-obra strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .datos-obra span { color: var(--ink-tertiary); font-size: var(--texto-xs); }

  .detalle-biblioteca { overflow-y: auto; padding: clamp(1.1rem, 2.7vw, 2.4rem); scrollbar-width: thin; }
  .presentacion-obra { display: grid; grid-template-columns: clamp(8rem, 17vw, 12rem) minmax(0,1fr); align-items: center; gap: clamp(1.2rem, 3vw, 2.7rem); padding: .6rem .7rem 2rem; border-block-end: 1px solid var(--trazo-suave); }
  .cubierta-grande { position: relative; aspect-ratio: .72; display: grid; place-items: center; border-radius: 5px 13px 13px 5px; overflow: hidden; color: var(--book-cover-ink); background: radial-gradient(circle at 75% 25%, var(--book-cover-glint) 0 3px, transparent 4px), linear-gradient(145deg, var(--book-cover-start), var(--book-cover-end)); box-shadow: inset 8px 0 12px var(--book-cover-thread), 0 20px 34px var(--book-cover-shadow); }
  .cubierta-grande::before { content: ''; position: absolute; inset: 0 auto 0 9px; inline-size: 1px; background: var(--book-cover-detail); }
  .cubierta-grande span { font: 800 clamp(2rem, 5vw, 4rem)/1 ui-serif, Georgia, serif; }
  .cubierta-grande i { position: absolute; inset: auto 13% 16%; block-size: 1px; background: var(--book-cover-detail); }
  .metadatos h2 { margin: .35rem 0 .5rem; max-inline-size: 34rem; color: var(--ink-primary); font: 700 clamp(1.45rem, 3vw, 2.35rem)/1.13 ui-serif, Georgia, serif; letter-spacing: -.025em; }
  .metadatos p { margin: 0 0 1.3rem; color: var(--ink-secondary); }
  .abrir-principal { display: inline-flex; align-items: center; gap: .5rem; min-block-size: 42px; padding: .6rem 1rem; border: 1px solid transparent; border-radius: 999px; background: var(--accent-main); color: var(--surface-paper); font: inherit; font-size: var(--texto-sm); font-weight: 700; cursor: pointer; box-shadow: var(--shadow-soft); }

  .partes { padding: 1.5rem .7rem .7rem; }
  .cabecera-partes { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; margin-block-end: .8rem; }
  .cabecera-partes h3 { margin: .18rem 0 0; color: var(--ink-primary); font-size: var(--texto-md); }
  .cabecera-partes > span { padding: .2rem .55rem; border-radius: 999px; background: var(--surface-canvas); color: var(--ink-secondary); font-size: var(--texto-xs); }
  .partes button { inline-size: 100%; display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: .8rem; padding: .75rem .85rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; text-align: start; cursor: pointer; transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
  .partes button:hover { transform: translateY(-1px); border-color: var(--accent-main); box-shadow: var(--shadow-soft); }
  .numero { color: var(--accent-main); font: 700 .72rem/1 var(--fuente-mono); }
  .datos-parte { min-inline-size: 0; display: flex; flex-direction: column; gap: .18rem; }
  .datos-parte strong { overflow: hidden; color: var(--ink-primary); font-size: var(--texto-sm); text-overflow: ellipsis; white-space: nowrap; }
  .datos-parte span { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .aviso-fragmentos { display: flex; align-items: center; justify-content: space-between; gap: .8rem; padding: .75rem .85rem; border: 1px solid var(--semantic-warning); border-radius: var(--radius-sm); background: var(--semantic-warning-bg); color: var(--ink-secondary); font-size: var(--texto-xs); }
  .aviso-fragmentos button { flex-shrink: 0; padding: .4rem .65rem; border: 1px solid var(--accent-main); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--accent-main); font: inherit; font-weight: 700; cursor: pointer; }
  .estado { margin: 1rem; color: var(--ink-tertiary); font-size: var(--texto-sm); }
  .vacia { min-block-size: 100%; display: grid; place-content: center; justify-items: center; text-align: center; color: var(--accent-main); }
  .vacia h2 { margin: .7rem 0 .2rem; color: var(--ink-primary); }
  .vacia p { margin: 0; color: var(--ink-secondary); }

  @media (max-width: 48rem) {
    .estanteria.con-seleccion .catalogo { display: none; }
    .estanteria:not(.con-seleccion) .detalle-biblioteca { display: none; }
    .con-seleccion .volver-catalogo { display: inline-flex; }
    .biblioteca { padding: var(--espacio-xs); overflow-y: auto; }
    .cabecera-biblioteca { align-items: flex-start; }
    .privada { display: none; }
    .estanteria { display: flex; flex: 0 0 auto; flex-direction: column; overflow: visible; }
    .catalogo, .detalle-biblioteca { flex: 0 0 auto; box-sizing: border-box; }
    .catalogo, .detalle-biblioteca { overflow: visible; }
    .catalogo { max-block-size: none; overflow-y: auto; }
    .presentacion-obra { grid-template-columns: 6.5rem minmax(0,1fr); gap: 1rem; padding-inline: 0; }
    .metadatos h2 { font-size: 1.3rem; }
    .partes { padding-inline: 0; }
    .aviso-fragmentos { align-items: flex-start; flex-direction: column; }
  }

  @media (prefers-reduced-motion: reduce) {
    .catalogo button, .partes button { transition: none; }
  }
</style>
