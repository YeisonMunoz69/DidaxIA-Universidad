
<script>
  import { onMount } from 'svelte';
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import Boton from '../base/Boton.svelte';
  import Icono from '../base/Icono.svelte';
  import Degradacion from '../estado/Degradacion.svelte';
  import * as api from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let {
    clase = null,
    titulo = 'Solicitudes de matrícula',
    alCambiar = () => {},
    alActualizar = () => {}
  } = $props();

  let solicitudes = $state([]);
  let cargando = $state(true);
  let resolviendo = $state('');
  let fallo = $state(null);
  let activo = false, consulta = null, controlConsulta = null;

  const visibles = $derived(
    solicitudes.filter((s) => s.estado === 'pendiente' && (!clase || s.clase_destino?.id === clase))
  );

  async function cargar({ silencioso = false } = {}) {
    if (!activo || (silencioso && (resolviendo || document.visibilityState !== 'visible'))) return;
    if (consulta) {
      if (silencioso) return;
      await consulta;
    }
    if (!activo) return;
    if (!silencioso) { cargando = true; fallo = null; }
    const control = new AbortController();
    controlConsulta = control;
    const tarea = (async () => {
      try {
        const nuevas = (await api.solicitudes({ señal: control.signal })) ?? [];
        if (!activo || control.signal.aborted) return;
        solicitudes = nuevas; fallo = null; alActualizar(nuevas);
      } catch (e) {
        if (activo && !control.signal.aborted && !silencioso) fallo = describir(e);
      } finally {
        if (activo && !silencioso) cargando = false;
      }
    })();
    consulta = tarea;
    await tarea;
    if (consulta === tarea) { consulta = null; controlConsulta = null; }
  }

  async function resolver(solicitud, decision) {
    if (resolviendo || !activo) return;
    resolviendo = solicitud.id;
    fallo = null;
    try {
      if (decision === 'aprobar') await api.aprobarSolicitud(solicitud.id);
      else await api.rechazarSolicitud(solicitud.id);
      await cargar();
      await alCambiar();
    } catch (e) {
      fallo = describir(e);
    } finally {
      resolviendo = '';
    }
  }

  function identidadDe(solicitud) {
    const nombre = String(solicitud.nombre_estudiante ?? '').trim();
    if (nombre) return nombre;
    const id = String(solicitud.estudiante ?? '');
    return `Estudiante ${id.slice(-8) || 'sin nombre disponible'}`;
  }

  function fechaLegible(valor) {
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return 'Fecha no disponible';
    return new Intl.DateTimeFormat('es-CO', {
      day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit'
    }).format(fecha);
  }

  onMount(() => {
    activo = true; void cargar();
    const actualizar = () => void cargar({ silencioso: true });
    const intervalo = setInterval(actualizar, 5000);
    window.addEventListener('focus', actualizar);
    document.addEventListener('visibilitychange', actualizar);
    return () => {
      activo = false; clearInterval(intervalo); controlConsulta?.abort();
      window.removeEventListener('focus', actualizar);
      document.removeEventListener('visibilitychange', actualizar);
    };
  });
</script>

<section class="bandeja" aria-labelledby="titulo-solicitudes">
  <header>
    <div>
      <h3 id="titulo-solicitudes">{titulo}</h3>
      <p>El ingreso o cambio sólo se hace efectivo al aprobarlo.</p>
    </div>
    <span class="contador" aria-label={`${visibles.length} solicitudes pendientes`}>
      {visibles.length}
    </span>
  </header>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {:else if cargando}
    <CargadorCubo mensaje="Cargando solicitudes…" />
  {:else if visibles.length}
    <ul>
      {#each visibles as solicitud (solicitud.id)}
        <li>
          <span class="avatar" aria-hidden="true">{identidadDe(solicitud).charAt(0)}</span>
          <span class="identidad">
            <strong>{identidadDe(solicitud)}</strong>
            <span>
              {#if solicitud.clase_origen}
                Cambio de {solicitud.clase_origen.nombre} a {solicitud.clase_destino?.nombre}
              {:else}
                Ingreso a {solicitud.clase_destino?.nombre}
              {/if}
            </span>
            <small>Solicitado el {fechaLegible(solicitud.creada_en)}</small>
            {#if solicitud.perfil_estudiante}
              <small class="perfil-academico">
                {solicitud.perfil_estudiante.facultad || 'Facultad pendiente'}
                {solicitud.perfil_estudiante.programa ? ` · ${solicitud.perfil_estudiante.programa}` : ''}
                {solicitud.perfil_estudiante.semestre ? ` · semestre ${solicitud.perfil_estudiante.semestre}` : ''}
              </small>
            {/if}
          </span>
          <span class="acciones">
            <Boton variante="secundario" onclick={() => resolver(solicitud, 'rechazar')}
                   deshabilitado={Boolean(resolviendo)}>
              Rechazar
            </Boton>
            <Boton onclick={() => resolver(solicitud, 'aprobar')}
                   deshabilitado={Boolean(resolviendo)}>
              <Icono nombre="check" medida={13} />
              {resolviendo === solicitud.id ? 'Resolviendo…' : 'Aprobar'}
            </Boton>
          </span>
        </li>
      {/each}
    </ul>
  {:else}
    <div class="vacio">
      <span aria-hidden="true"><Icono nombre="check" medida={22} /></span>
      <strong>No hay solicitudes pendientes</strong>
      <p>Las nuevas peticiones aparecerán aquí sin recargar la clase.</p>
    </div>
  {/if}
</section>

<style>
  .bandeja { display: flex; min-block-size: 0; flex-direction: column; gap: var(--espacio-md); }
  header { display: flex; align-items: center; justify-content: space-between; gap: var(--espacio-md); padding-block-end: .65rem; border-block-end: 1px solid var(--trazo-suave); }
  h3 { margin: 0; color: var(--ink-primary); font-size: var(--texto-md); }
  header p { margin: .2rem 0 0; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .contador { display: grid; place-items: center; min-inline-size: 1.8rem; block-size: 1.8rem; padding-inline: .4rem; border-radius: 999px; background: var(--accent-surface); color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; }
  ul { display: grid; gap: .65rem; margin: 0; padding: 0; list-style: none; overflow-y: auto; }
  li { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; align-items: center; gap: .8rem; padding: .75rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .avatar { display: grid; place-items: center; inline-size: 42px; block-size: 42px; border: 1.5px solid var(--accent-main); border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); font-weight: 800; }
  .identidad { display: flex; min-inline-size: 0; flex-direction: column; gap: .15rem; }
  .identidad strong, .identidad span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .identidad strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .identidad span { color: var(--ink-secondary); font-size: var(--texto-xs); }
  .identidad small { color: var(--ink-tertiary); }
  .identidad .perfil-academico { overflow-wrap: anywhere; }
  .acciones { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .45rem; }
  .vacio { display: grid; place-items: center; gap: .4rem; min-block-size: 13rem; padding: var(--espacio-xl); text-align: center; color: var(--ink-secondary); }
  .vacio > span { display: grid; place-items: center; inline-size: 50px; block-size: 50px; border-radius: 50%; background: var(--semantic-success-bg); color: var(--semantic-success); }
  .vacio strong { color: var(--ink-primary); }
  .vacio p { margin: 0; font-size: var(--texto-xs); }
  @media (max-width: 42rem) {
    li { grid-template-columns: 40px minmax(0, 1fr); }
    .acciones { grid-column: 1 / -1; }
    .acciones :global(.boton) { flex: 1; }
  }
</style>
