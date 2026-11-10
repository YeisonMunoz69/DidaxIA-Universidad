<!-- Directorio de acceso a las fichas, paginado por el servidor de 10 en 10. -->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { untrack } from 'svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import EstadoVacio from './EstadoVacio.svelte';
  import * as api from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let {
    rol = 'docente',
    alElegir = () => {}
  } = $props();

  let pagina = $state(1);
  let datos = $state(null);
  let cargando = $state(true);
  let fallo = $state(null);
  let peticion = 0;
  let textoBusqueda = $state('');
  let busqueda = $state('');

  async function cargar() {
    const actual = ++peticion;
    cargando = true;
    fallo = null;
    try {
      const funcion = rol === 'investigador'
        ? api.directorioInstitucionalDeEstudiantes
        : api.directorioDeEstudiantes;
      const nuevos = await funcion(pagina, ...(rol === 'investigador' && busqueda ? [{buscar:busqueda}] : []));
      if (actual === peticion) datos = nuevos;
    } catch (error) {
      if (actual === peticion) fallo = describir(error);
    } finally {
      if (actual === peticion) cargando = false;
    }
  }

  $effect(() => {
    void pagina;
    void rol;
    void busqueda;
    untrack(() => cargar());
  });

  function inicial(nombre) {
    return String(nombre || 'E').trim().charAt(0).toLocaleUpperCase('es') || 'E';
  }

  function buscar(evento) {
    evento.preventDefault();
    const nueva=textoBusqueda.trim();
    if (pagina === 1 && busqueda === nueva) { void cargar(); return; }
    pagina=1;busqueda=nueva;
  }

  function limpiarBusqueda() {
    textoBusqueda='';pagina=1;busqueda='';
  }
</script>

{#if fallo}
  <Degradacion respuesta={fallo} alReintentar={cargar} />
{:else if cargando && !datos}
  <CargadorCubo mensaje="Organizando el directorio alfabético…" pantallaCompleta />
{:else if datos}
  <section class="directorio" aria-labelledby="titulo-directorio" aria-busy={cargando}>
    <header>
      <div>
        <span class="sobrelinea">SEGUIMIENTO ACADÉMICO</span>
        <h2 id="titulo-directorio">Alumnos matriculados</h2>
        <p>{rol === 'investigador'
          ? 'Estudiantes de las clases registradas en la institución.'
          : 'Estudiantes matriculados en tus clases.'}</p>
      </div>
      {#if rol === 'investigador'}
        <form class="busqueda" role="search" onsubmit={buscar} aria-label="Buscar estudiantes en el directorio">
          <label for="busqueda-directorio">Nombre o correo institucional</label>
          <div><input id="busqueda-directorio" type="search" bind:value={textoBusqueda} maxlength="200" placeholder="Buscar estudiante…" />
            <button type="submit" aria-label="Buscar estudiante"><Icono nombre="buscar" medida={18} /></button>
            {#if textoBusqueda || busqueda}<button type="button" onclick={limpiarBusqueda} aria-label="Limpiar búsqueda"><Icono nombre="cerrar" medida={18} /></button>{/if}
          </div>
        </form>
      {/if}
      <span class="total">{datos.total} {busqueda ? 'coincidencia' : 'alumno'}{datos.total === 1 ? '' : 's'}</span>
    </header>

    {#if cargando}
      <p class="actualizando" role="status">Actualizando el directorio…</p>
    {/if}

    <div class="lista">
      {#each datos.estudiantes ?? [] as estudiante (estudiante.identificador)}
        <button type="button" onclick={() => alElegir(estudiante)}>
          <span class="avatar">
            <span aria-hidden="true">{inicial(estudiante.nombre)}</span>
            {#if estudiante.tiene_foto}
              <img src={api.fotoDeIntegrante(estudiante.clase.id, estudiante.identificador)}
                   alt={`Foto de perfil de ${estudiante.nombre}`}
                   onerror={(evento) => (evento.currentTarget.hidden = true)} />
            {/if}
          </span>
          <span class="datos">
            <strong>{estudiante.nombre}</strong>
            <span>{estudiante.clase?.nombre || 'Clase sin nombre'}</span>
            <small>
              {estudiante.facultad || 'Facultad pendiente'}
              {estudiante.programa ? ` · ${estudiante.programa}` : ''}
              {estudiante.semestre ? ` · semestre ${estudiante.semestre}` : ''}
            </small>
          </span>
          <span class="abrir"><span>Ver ficha</span><Icono nombre="flecha-der" medida={18} /></span>
        </button>
      {:else}
        <EstadoVacio icono="estudiante" tono="neutro" titulo={busqueda ? 'No hay estudiantes que coincidan' : 'Todavía no hay alumnos matriculados'}
          texto={busqueda ? 'Prueba otro nombre o correo, o limpia la búsqueda para ver el directorio completo.' : rol === 'investigador'
            ? 'El directorio se llenará cuando existan matrículas aprobadas en alguna clase.'
            : 'Los alumnos aparecerán aquí después de que apruebes sus solicitudes de matrícula.'} />
      {/each}
    </div>

    {#if datos.total > 0}
      <nav class="paginacion" aria-label="Páginas del directorio">
        <button type="button" disabled={pagina <= 1 || cargando} onclick={() => (pagina -= 1)}>
          <Icono nombre="flecha-izq" medida={16} /> Anterior
        </button>
        <span>Página <strong>{datos.pagina}</strong> de <strong>{datos.paginas}</strong></span>
        <button type="button" disabled={pagina >= datos.paginas || cargando} onclick={() => (pagina += 1)}>
          Siguiente <Icono nombre="flecha-der" medida={16} />
        </button>
      </nav>
    {/if}
  </section>
{/if}

<style>
  .busqueda { margin-inline-start: auto; min-inline-size: 0; inline-size: min(100%, 26rem); }
  .busqueda label { display: block; font-size: var(--texto-xs); color: var(--ink-secondary); margin-block-end: .3rem; }
  .busqueda > div { display: flex; gap: .35rem; }
  .busqueda input { min-inline-size: 0; flex: 1; padding: .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .busqueda button { flex: 0 0 auto; display: grid; place-items: center; min-inline-size: 44px; min-block-size: 44px; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--accent-main); cursor: pointer; }
  @media (max-width: 52rem) { header { flex-wrap: wrap; } .busqueda { order: 3; inline-size: 100%; } }
  .actualizando { margin: 0; padding: 1.5rem; color: var(--ink-tertiary); text-align: center; }
  .directorio { position: relative; display: grid; gap: 1rem; padding: 1.15rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  header { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; padding-block-end: .9rem; border-block-end: 1px solid var(--trazo-suave); }
  header div { min-inline-size: 0; }
  .sobrelinea { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; }
  h2 { margin: .18rem 0; color: var(--ink-primary); font-size: var(--texto-lg); }
  header p { margin: 0; max-inline-size: none; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .total { flex: 0 0 auto; padding: .35rem .6rem; border-radius: 999px; background: var(--accent-surface); color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; }
  .actualizando { position: absolute; inset: 5rem 1rem auto; z-index: 1; padding: .45rem; border-radius: 999px; background: var(--surface-elevated); box-shadow: var(--shadow-soft); font-size: var(--texto-xs); }
  .lista { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .7rem; }
  .lista > button { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: .75rem; min-block-size: 5.35rem; padding: .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-primary); font: inherit; text-align: start; cursor: pointer; transition: var(--transition-fast); }
  .lista > button:hover, .lista > button:focus-visible { border-color: var(--accent-main); background: var(--accent-surface); transform: translateY(-1px); box-shadow: var(--shadow-soft); }
  .avatar { position: relative; display: grid; place-items: center; inline-size: 2.75rem; block-size: 2.75rem; overflow: hidden; border: 1px solid var(--accent-main); border-radius: 50%; background: var(--surface-paper); color: var(--accent-main); font-weight: 800; }
  .avatar img { position: absolute; inset: 0; inline-size: 100%; block-size: 100%; object-fit: cover; }
  .datos { display: grid; gap: .12rem; min-inline-size: 0; }
  .datos strong, .datos span, .datos small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .datos strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .datos span { color: var(--ink-secondary); font-size: var(--texto-xs); }
  .datos small { color: var(--ink-tertiary); font-size: 10.5px; }
  .abrir { display: inline-flex; align-items: center; gap: .3rem; color: var(--accent-main); font-size: var(--texto-xs); font-weight: 750; }
  .paginacion { display: flex; align-items: center; justify-content: center; gap: 1rem; padding-block-start: .25rem; }
  .paginacion button { display: inline-flex; align-items: center; gap: .35rem; min-block-size: 2.35rem; padding: .4rem .7rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; font-size: var(--texto-xs); font-weight: 750; cursor: pointer; }
  .paginacion button:not(:disabled):hover { border-color: var(--accent-main); color: var(--accent-main); }
  .paginacion button:disabled { cursor: not-allowed; opacity: .45; }
  .paginacion > span { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .paginacion strong { color: var(--ink-primary); }
  @media (max-width: 52rem) { .lista { grid-template-columns: 1fr; } }
  @media (max-width: 36rem) {
    .directorio { padding: .85rem; }
    header { align-items: flex-start; }
    .lista > button { grid-template-columns: auto minmax(0, 1fr); }
    .abrir { grid-column: 2; }
    .abrir span { display: none; }
    .paginacion { justify-content: space-between; gap: .4rem; }
    .paginacion button { padding-inline: .55rem; }
  }
</style>
