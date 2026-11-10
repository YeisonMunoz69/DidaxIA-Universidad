<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import * as api from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import Boton from '../../comun/base/Boton.svelte';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';
  import { CAMINOS } from '../../enrutado/caminos.js';

  let {
    clase = '',
    rol = 'docente',
    vista = 'estadisticas',
    alElegir = null,
    proyectar = $bindable(false)
  } = $props();
  let datos = $state(null);
  let cargando = $state(false);
  let error = $state('');
  let metrica = $state('turnos');
  let busqueda = $state('');
  let soloActivos = $state(false);
  let revision = $state(0);
  let desde = $state(fechaLocal(-7));
  let hasta = $state(fechaLocal(1));

  const etiquetas = {
    turnos: 'Turnos elegibles',
    conversaciones: 'Conversaciones',
    dias: 'Días activos',
    recencia: 'Actividad reciente',
    cobertura: 'Cobertura de evidencia'
  };

  function fechaLocal(desplazamiento) {
    const fecha = new Date(Date.now() + desplazamiento * 86400000);
    const partes = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(fecha);
    const de = (tipo) => partes.find((parte) => parte.type === tipo)?.value;
    return `${de('year')}-${de('month')}-${de('day')}`;
  }

  function periodo() {
    return {
      desde: `${desde}T00:00:00-05:00`,
      hasta: `${hasta}T00:00:00-05:00`
    };
  }

  function valorPrincipal(estudiante) {
    if (metrica === 'conversaciones') return estudiante.conversaciones;
    if (metrica === 'dias') return estudiante.dias_activos;
    if (metrica === 'recencia') return estudiante.ultima_actividad ? fecha(estudiante.ultima_actividad, true) : 'Sin actividad';
    if (metrica === 'cobertura') return estudiante.cobertura_evidencia == null ? 'Sin muestra' : `${Math.round(estudiante.cobertura_evidencia * 100)}%`;
    return estudiante.turnos_elegibles;
  }

  function fecha(valor, corta = false) {
    const instante = new Date(valor);
    if (Number.isNaN(instante.getTime())) return 'No disponible';
    return new Intl.DateTimeFormat('es-CO', corta
      ? { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }
      : { dateStyle: 'medium', timeStyle: 'short' }
    ).format(instante);
  }

  function nombreDe(estudiante) {
    return proyectar ? estudiante.alias_proyeccion : estudiante.nombre;
  }

  function destinoFicha(estudiante) {
    return `${CAMINOS.estudiante}?clase=${encodeURIComponent(clase)}&id=${encodeURIComponent(estudiante.identificador)}`;
  }

  function abrirFicha(evento, estudiante) {
    if (!alElegir || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey || evento.button > 0) return;
    evento.preventDefault();
    alElegir({ identificador: estudiante.identificador, clase: { id: clase } });
  }

  function tendenciaDe(valor) {
    return {
      aumenta: 'Aumenta', disminuye: 'Disminuye', estable: 'Estable', sin_actividad: 'Sin actividad'
    }[valor] ?? 'No disponible';
  }

  async function cargar(controlador = new AbortController()) {
    if (!clase) return;
    cargando = true;
    error = '';
    try {
      const funcion = rol === 'investigador'
        ? api.actividadInstitucionalDeClase
        : api.actividadDeClase;
      datos = await funcion(clase, {
        ...periodo(), metrica, busqueda: busqueda.trim(), activos: soloActivos,
        señal: controlador.signal
      });
    } catch (e) {
      if (e?.name !== 'AbortError') error = describir(e)?.mensaje ?? 'No se pudo actualizar la actividad.';
    } finally {
      if (!controlador.signal.aborted) cargando = false;
    }
  }

  $effect(() => {
    void clase; void rol; void desde; void hasta; void metrica; void busqueda; void soloActivos; void revision;
    const controlador = new AbortController();
    const actualizar = () => {
      if (globalThis.document?.visibilityState !== 'hidden') void cargar(controlador);
    };
    actualizar();
    const intervalo = globalThis.setInterval(actualizar, 15000);
    globalThis.document?.addEventListener('visibilitychange', actualizar);
    return () => {
      controlador.abort();
      globalThis.clearInterval(intervalo);
      globalThis.document?.removeEventListener('visibilitychange', actualizar);
    };
  });

  const podio = $derived((datos?.estudiantes ?? []).filter((e) => e.posicion <= 3));
  const resumen = $derived.by(() => {
    const estudiantes = datos?.estudiantes ?? [];
    return {
      estudiantes: estudiantes.length,
      activos: estudiantes.filter((e) => e.turnos_elegibles > 0).length,
      turnos: estudiantes.reduce((total, e) => total + Number(e.turnos_elegibles || 0), 0),
      conversaciones: estudiantes.reduce((total, e) => total + Number(e.conversaciones || 0), 0)
    };
  });
</script>

<section class="actividad" aria-labelledby="actividad-clase-titulo">
  <header>
    <div>
      <span class="sobrelinea">USO DURANTE EL PERÍODO</span>
      <h3 id="actividad-clase-titulo">Actividad de la clase</h3>
      <p>No representa aprendizaje, nota ni “mejores estudiantes”. Ordena una métrica observable a la vez.</p>
    </div>
    <div class="estado-actualizacion">
      <small>{datos?.actualizado_en ? `Actualizado ${fecha(datos.actualizado_en, true)}` : 'Aún sin actualizar'}</small>
      <Boton variante="secundario" onclick={() => (revision += 1)} deshabilitado={cargando}>
        {cargando ? 'Actualizando…' : 'Actualizar'}
      </Boton>
    </div>
  </header>

  <div class="filtros">
    <SelectorFecha etiqueta="Desde" bind:value={desde} maximo={fechaLocal(0)} />
    <SelectorFecha etiqueta="Hasta (exclusivo)" bind:value={hasta} minimo={desde} maximo={fechaLocal(1)} exclusivo />
    <label>Métrica
      <select use:menuDesplegable={metrica} bind:value={metrica}>
        {#each Object.entries(etiquetas) as [valor, etiqueta]}<option value={valor}>{etiqueta}</option>{/each}
      </select>
    </label>
    <label>Buscar estudiante
      <input type="search" bind:value={busqueda} placeholder="Nombre" />
    </label>
    <label class="casilla"><input type="checkbox" bind:checked={soloActivos} /> Sólo con actividad</label>
    <label class="casilla"><input type="checkbox" bind:checked={proyectar} /> Modo para proyectar</label>
  </div>

  {#if proyectar}
    <p class="aviso-proyeccion" role="status">Se muestran alias y avatares; se ocultan nombres y fotografías. Esta vista no incluye edad, consentimiento, correo ni indicios sensibles.</p>
  {/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}

  {#if vista === 'estadisticas' && datos}
    <div class="resumen" aria-label="Resumen de actividad">
      <article><span>Estudiantes en la vista</span><strong>{resumen.estudiantes}</strong></article>
      <article><span>Con actividad</span><strong>{resumen.activos}</strong></article>
      <article><span>Turnos elegibles</span><strong>{resumen.turnos}</strong></article>
      <article><span>Conversaciones</span><strong>{resumen.conversaciones}</strong></article>
    </div>
  {/if}

  {#snippet identidad(estudiante)}
    <span class="avatar" aria-hidden="true">{#if !proyectar && estudiante.tiene_foto}<img src={api.fotoDeIntegrante(clase, estudiante.identificador)} alt="" loading="lazy" />{:else}{nombreDe(estudiante).charAt(0)}{/if}</span>
    <span>{nombreDe(estudiante)}</span>
  {/snippet}
  {#snippet contenidoPodio(estudiante)}
    <strong>#{estudiante.posicion}</strong>
    {@render identidad(estudiante)}
    <b>{valorPrincipal(estudiante)}</b>
  {/snippet}
  {#if vista === 'ranking' && podio.length}
    <div class="podio" aria-label={`Primeras posiciones por ${etiquetas[metrica]}`}>
      {#each podio as estudiante (estudiante.identificador)}
        {#if proyectar}
          <article class="tarjeta-podio" class:primero={estudiante.posicion === 1}>{@render contenidoPodio(estudiante)}</article>
        {:else}
          <a class="tarjeta-podio" class:primero={estudiante.posicion === 1} href={destinoFicha(estudiante)}
            aria-label={`Abrir ficha de ${estudiante.nombre}`} onclick={(evento) => abrirFicha(evento, estudiante)}>{@render contenidoPodio(estudiante)}</a>
        {/if}
      {/each}
    </div>
  {/if}

  <div class="tabla-contenedor">
    <table>
      <caption>Participación en DidaxIa · {datos?.clase?.nombre ?? 'clase seleccionada'} · ordenada por {etiquetas[metrica]}</caption>
      {#if vista === 'ranking'}
        <thead><tr><th>Posición</th><th>Estudiante</th><th>{etiquetas[metrica]}</th><th>Tendencia</th><th>Última actividad</th></tr></thead>
      {:else}
        <thead><tr><th>Posición</th><th>Estudiante</th><th>Turnos</th><th>Conversaciones</th><th>Días</th><th>Última actividad</th><th>Promedio</th><th>Tendencia</th><th>Cobertura</th></tr></thead>
      {/if}
      <tbody>
        {#if cargando && !datos}
          <tr><td colspan={vista === 'ranking' ? 5 : 9} class="vacio"><CargadorCubo mensaje="Cargando la actividad de la clase…" compacto /></td></tr>
        {/if}
        {#each datos?.estudiantes ?? [] as estudiante (estudiante.identificador)}
          <tr>
            <td data-label="Posición"><strong>#{estudiante.posicion}</strong></td>
            <td data-label="Estudiante">
              {#if proyectar}<span class="persona">{@render identidad(estudiante)}</span>
              {:else}<a class="persona" href={destinoFicha(estudiante)} aria-label={`Abrir ficha de ${estudiante.nombre}`}
                onclick={(evento) => abrirFicha(evento, estudiante)}>{@render identidad(estudiante)}</a>{/if}
            </td>
            {#if vista === 'ranking'}
              <td data-label={etiquetas[metrica]}>{valorPrincipal(estudiante)}</td>
              <td data-label="Tendencia">{tendenciaDe(estudiante.tendencia)}</td>
              <td data-label="Última actividad">{estudiante.ultima_actividad ? fecha(estudiante.ultima_actividad, true) : 'Sin actividad'}</td>
            {:else}
              <td data-label="Turnos">{estudiante.turnos_elegibles}</td>
              <td data-label="Conversaciones">{estudiante.conversaciones}</td>
              <td data-label="Días activos">{estudiante.dias_activos}</td>
              <td data-label="Última actividad">{estudiante.ultima_actividad ? fecha(estudiante.ultima_actividad, true) : 'Sin actividad'}</td>
              <td data-label="Promedio de turnos">{estudiante.promedio_turnos ?? '—'}</td>
              <td data-label="Tendencia">{tendenciaDe(estudiante.tendencia)}</td>
              <td data-label="Cobertura">{estudiante.cobertura_evidencia == null ? 'Sin muestra' : `${Math.round(estudiante.cobertura_evidencia * 100)}%`}</td>
            {/if}
          </tr>
        {:else}
          {#if !cargando}<tr><td colspan={vista === 'ranking' ? 5 : 9} class="vacio">No hay estudiantes que coincidan con los filtros.</td></tr>{/if}
        {/each}
      </tbody>
    </table>
  </div>
  <footer>
    <small>Período: {desde} a {hasta} (exclusivo) · máximo {datos?.limite ?? 200} registros.</small>
    {#if datos?.truncado}<small>La respuesta fue limitada; ajusta la búsqueda.</small>{/if}
  </footer>
</section>

<style>
  .actividad { overflow: hidden; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .actividad > header { display: flex; justify-content: space-between; gap: 1rem; padding: 1rem; border-block-end: 1px solid var(--trazo-suave); }
  h3, p { margin: 0; } h3 { color: var(--ink-primary); } header p { margin-block-start: .25rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .sobrelinea { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; }
  .estado-actualizacion { display: grid; justify-items: end; gap: .4rem; color: var(--ink-tertiary); }
  .filtros { display: grid; grid-template-columns: repeat(4, minmax(10rem, 1fr)) repeat(2, auto); gap: .75rem; align-items: end; padding: .85rem 1rem; background: var(--surface-panel); }
  .filtros label { display: grid; gap: .25rem; color: var(--ink-secondary); font-size: var(--texto-xs); font-weight: 700; }
  select, input[type='search'] { min-block-size: 2.5rem; min-inline-size: 0; padding: .45rem .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .filtros .casilla { display: flex; align-items: center; gap: .4rem; min-block-size: 2.5rem; }
  .aviso-proyeccion, .error { padding: .7rem 1rem; font-size: var(--texto-sm); }
  .aviso-proyeccion { background: var(--accent-surface); color: var(--ink-secondary); }
  .error { background: var(--semantic-error-bg); color: var(--semantic-error); }
  .podio { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .6rem; padding: 1rem; }
  .resumen { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .65rem; padding: 1rem; }
  .resumen article { display: grid; gap: .2rem; padding: .75rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); }
  .resumen span { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .resumen strong { color: var(--ink-primary); font-size: var(--texto-xl); }
  .tarjeta-podio { display: grid; grid-template-columns: auto auto minmax(0, 1fr) auto; align-items: center; gap: .55rem; min-inline-size: 0; padding: .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); color:var(--ink-primary); text-decoration:none; }
  .tarjeta-podio.primero { border-color: var(--accent-main); background: var(--accent-surface); }
  .tarjeta-podio > span:not(.avatar) { overflow-wrap: anywhere; }
  a.tarjeta-podio:hover, a.persona:hover { background:var(--accent-surface); color:var(--accent-main); }
  a.tarjeta-podio:focus-visible, a.persona:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; }
  .avatar { position: relative; display: inline-grid; place-items: center; inline-size: 2rem; block-size: 2rem; flex: 0 0 auto; overflow: hidden; border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); font-weight: 800; }
  .avatar img { inline-size: 100%; block-size: 100%; object-fit: cover; }
  .tabla-contenedor { inline-size: 100%; }
  table { inline-size: 100%; border-collapse: collapse; font-size: var(--texto-xs); }
  caption { padding: .65rem 1rem; color: var(--ink-secondary); text-align: start; font-weight: 700; }
  th, td { padding: .6rem .5rem; border-block-start: 1px solid var(--trazo-suave); text-align: start; vertical-align: middle; }
  th { color: var(--ink-secondary); background: var(--surface-panel); }
  td { color: var(--ink-secondary); } td strong { color: var(--accent-main); }
  .persona { display: inline-flex; align-items: center; gap: .45rem; min-inline-size: 0; min-block-size:44px; color: var(--ink-primary); font-weight: 700; text-decoration:none; overflow-wrap:anywhere; }
  .vacio { padding: 1.25rem; text-align: center; color: var(--ink-tertiary); }
  footer { display: flex; justify-content: space-between; gap: .5rem; padding: .7rem 1rem; color: var(--ink-tertiary); border-block-start: 1px solid var(--trazo-suave); }
  @media (max-width: 64rem) { .filtros { grid-template-columns: repeat(2, 1fr); } .podio { grid-template-columns: 1fr; } .resumen { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 44rem) {
    .actividad > header, footer { flex-direction: column; }
    .estado-actualizacion { justify-items: start; }
    .filtros, .resumen { grid-template-columns: 1fr; }
    table, tbody, tr, td { display: block; }
    thead { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); }
    tr { padding: .65rem 1rem; border-block-start: 1px solid var(--trazo-suave); }
    td { display: grid; grid-template-columns: minmax(8rem, .8fr) minmax(0, 1.2fr); gap: .6rem; padding: .25rem 0; border: 0; overflow-wrap: anywhere; }
    td::before { content: attr(data-label); color: var(--ink-tertiary); font-weight: 700; }
    td.vacio { display: block; }
  }
  @media (prefers-reduced-motion: no-preference) { tbody tr { transition: background-color 140ms ease; } tbody tr:hover { background: var(--surface-panel); } }
</style>
